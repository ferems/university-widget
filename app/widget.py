from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from PySide6.QtCore import QObject, QPoint, QPointF, QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QGuiApplication, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QFrame, QHBoxLayout, QLabel, QLayout, QMenu,
                               QProgressBar, QPushButton, QScrollArea, QToolButton, QVBoxLayout, QWidget)

from . import formato, geometria, iconos, resumen
from .ajustes import Ajustes
from .config import INTERVALO_MINUTOS, ZONA
from .dialogos import AlertaUrgente, DialogoAjustes, DialogoConexion
from .modelos import Pendiente
from .notificaciones import Notificador
from .servicio import Resultado, Servicio
from .tareas import EstadoTareas

log = logging.getLogger(__name__)

AZUL, VERDE = QColor("#2563eb"), QColor("#059669")
URG_A, URG_B = QColor("#dc2626"), QColor("#7f1d1d")
PANEL = QColor("#111827")
TEXTO2 = "#9ca3af"


def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def hace(fecha_iso: str) -> str:
    try:
        d = datetime.fromisoformat(fecha_iso.replace("Z", "+00:00"))
    except ValueError:
        return ""
    s = int((datetime.now(timezone.utc) - d).total_seconds())
    if s < 3600:
        return "hace un momento" if s < 120 else f"hace {s // 60} min"
    if s < 86400:
        return f"hace {s // 3600} h"
    return f"hace {s // 86400} d"


class Trabajador(QObject):
    """Ejecuta la revision en segundo plano para que la ventana nunca se congele."""
    terminado = Signal(object)

    def __init__(self, servicio: Servicio):
        super().__init__()
        self.servicio = servicio
        self._ocupado = False

    def lanzar(self) -> bool:
        if self._ocupado:
            return False
        self._ocupado = True
        threading.Thread(target=self._run, daemon=True).start()
        return True

    def _run(self):
        try:
            res = self.servicio.refrescar()
        except Exception as e:  # nunca dejar caer la app
            log.exception("Error inesperado al actualizar")
            res = self.servicio.desde_cache(error=f"Error inesperado: {type(e).__name__}")
        self._ocupado = False
        self.terminado.emit(res)


class Clicable(QLabel):
    clic = Signal()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clic.emit()
            e.accept()
        else:
            super().mousePressEvent(e)


class Tarjeta(QFrame):
    """Caja redondeada de la lista."""

    def __init__(self, k: float, borde: str = "transparent"):
        super().__init__()
        self.setStyleSheet(f"Tarjeta{{background:rgba(255,255,255,0.06);border-radius:{round(8*k)}px;"
                           f"border-left:{round(3*k)}px solid {borde};}}")


class WidgetCanvas(QWidget):
    def __init__(self, servicio: Servicio, notificador: Notificador, app, ajustes: Ajustes | None = None,
                 tareas: EstadoTareas | None = None):
        super().__init__()
        self.servicio, self.notificador, self.app = servicio, notificador, app
        self.ajustes = ajustes or Ajustes()
        self.tareas = tareas or EstadoTareas()
        self.res = Resultado()
        self.pendientes: List[Pendiente] = []
        self.expandido = False
        self.ancla = "tl"
        self.tab = "pend"
        self.filtro_curso: Optional[str] = None
        self._parpadeo = False
        self._arrastre: Optional[QPoint] = None
        self._movido = False
        self._clic_en_cabecera = False
        self._hover = False
        self._alertas: list = []
        self._alertados: set = set()
        self._pidio_conexion = False
        self._reintento = False
        self.n_activos = 0

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self.trabajador = Trabajador(servicio)
        self.trabajador.terminado.connect(self.al_terminar)
        self.t_seg = QTimer(self, interval=1000, timeout=self.cada_segundo)
        self.t_parpadeo = QTimer(self, interval=600, timeout=self._alternar)
        self.t_auto = QTimer(self, interval=INTERVALO_MINUTOS * 60 * 1000, timeout=self.actualizar_ahora)
        self.t_prog = QTimer(self, interval=30_000, timeout=self.revisar_programados)
        self.t_res = QTimer(self, interval=60_000, timeout=self.revisar_resumen)
        self.t_leave = QTimer(self, singleShot=True, interval=350, timeout=self._salio)
        for t in (self.t_seg, self.t_auto, self.t_prog, self.t_res):
            t.start()

        self._construir()
        self.al_terminar(servicio.desde_cache(), notificar=False)
        self._colocar_inicial()

    # ------------------------------------------------------------------ tamano
    def px(self, n: float) -> int:
        return max(1, round(n * self.k))

    @property
    def k(self) -> float:
        return float(self.ajustes["escala"])

    def _tam_icono(self):
        lado = self.px(60) + 2 * self.px(7)
        return lado, lado

    def _tam_panel(self):
        geo = self.screen().availableGeometry()
        return self.px(390), min(self.px(580), geo.height() - 40)

    # ------------------------------------------------------------------ construccion
    def _construir(self):
        """Crea (o recrea, si cambia el tamano) todos los controles del panel."""
        anterior = getattr(self, "panel", None)
        if anterior is not None:  # se recrea al cambiar el tamano
            anterior.hide()
            anterior.setParent(None)
            anterior.deleteLater()
        viejo = self.layout()
        if viejo is not None:
            QWidget().setLayout(viejo)  # suelta el layout anterior
        self.panel = QWidget(self)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSizeConstraint(QLayout.SetNoConstraint)
        raiz.addWidget(self.panel)
        px = self.px
        self.panel.setStyleSheet(f"QLabel{{color:white;background:transparent;font-size:{px(12)}px;}}")

        pl = QVBoxLayout(self.panel)
        pl.setContentsMargins(px(14), px(10), px(14), px(12))
        pl.setSpacing(px(6))

        # cabecera (arrastra la ventana; un clic la contrae)
        self.cab = QWidget()
        self.cab.setFixedHeight(px(50))
        ch = QHBoxLayout(self.cab)
        ch.setContentsMargins(0, 0, 0, 0)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.l_titulo = QLabel("Canvas")
        self.l_titulo.setStyleSheet(f"font-size:{px(17)}px;font-weight:700;color:white;")
        self.l_resumen = QLabel("")
        self.l_resumen.setStyleSheet(f"font-size:{px(11)}px;color:{TEXTO2};")
        col.addWidget(self.l_titulo)
        col.addWidget(self.l_resumen)
        ch.addLayout(col, 1)
        est_b = (f"QToolButton{{color:white;background:rgba(255,255,255,0.10);border:none;border-radius:{px(14)}px;"
                 f"font-size:{px(14)}px;}} QToolButton:hover{{background:rgba(255,255,255,0.22);}}")
        for texto, fn, tip in (("⚙", self.abrir_ajustes, "Ajustes"), ("▾", self.contraer, "Contraer a ícono")):
            b = QToolButton()
            b.setText(texto)
            b.setToolTip(tip)
            b.setFixedSize(px(28), px(28))
            b.setStyleSheet(est_b)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            ch.addWidget(b)
        pl.addWidget(self.cab)

        self.barra = QProgressBar()
        self.barra.setTextVisible(False)
        self.barra.setFixedHeight(px(6))
        self.barra.setStyleSheet(f"QProgressBar{{background:rgba(255,255,255,0.12);border:none;border-radius:{px(3)}px;}}"
                                 f"QProgressBar::chunk{{background:#10b981;border-radius:{px(3)}px;}}")
        pl.addWidget(self.barra)

        self.l_estado = QLabel("")
        self.l_estado.setWordWrap(True)
        self.l_estado.setStyleSheet(f"color:#fcd34d;font-size:{px(11)}px;")
        pl.addWidget(self.l_estado)

        # pestanas
        fila = QHBoxLayout()
        fila.setSpacing(px(4))
        self.grupo_tabs = QButtonGroup(self)
        self.botones_tab = {}
        est_t = (f"QPushButton{{color:{TEXTO2};background:transparent;border:none;border-radius:{px(8)}px;"
                 f"padding:{px(6)}px {px(4)}px;font-size:{px(11)}px;font-weight:600;}}"
                 f"QPushButton:checked{{color:white;background:rgba(255,255,255,0.16);}}"
                 f"QPushButton:hover{{background:rgba(255,255,255,0.10);}}")
        for clave in ("pend", "cursos", "anuncios", "notas"):
            b = QPushButton()
            b.setCheckable(True)
            b.setStyleSheet(est_t)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=clave: self.cambiar_tab(c))
            self.grupo_tabs.addButton(b)
            fila.addWidget(b, 1)
            self.botones_tab[clave] = b
        pl.addLayout(fila)

        self.lista = QWidget()
        self.lista.setStyleSheet("background:transparent;")
        self.lista_lay = QVBoxLayout(self.lista)
        self.lista_lay.setContentsMargins(0, 0, px(4), 0)
        self.lista_lay.setSpacing(px(5))
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;} QScrollArea>QWidget>QWidget{background:transparent;}"
            f"QScrollBar:vertical{{background:transparent;width:{px(7)}px;}}"
            "QScrollBar::handle:vertical{background:rgba(255,255,255,0.25);border-radius:3px;}"
            "QScrollBar::add-line,QScrollBar::sub-line{height:0;}")
        self.scroll.setWidget(self.lista)
        pl.addWidget(self.scroll, 1)

        pie = QHBoxLayout()
        est_p = (f"QPushButton{{color:white;background:rgba(255,255,255,0.12);border:none;border-radius:{px(6)}px;"
                 f"padding:{px(5)}px {px(8)}px;font-size:{px(11)}px;}} QPushButton:hover{{background:rgba(255,255,255,0.24);}}")
        for texto, fn in (("Actualizar ahora", self.actualizar_ahora), ("Probar notificación", self.probar_notificacion),
                          ("Conexión…", self.abrir_conexion)):
            b = QPushButton(texto)
            b.setStyleSheet(est_p)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            pie.addWidget(b)
        pl.addLayout(pie)

        self.panel.setVisible(self.expandido)
        ancho, alto = self._tam_icono() if not self.expandido else self._tam_panel()
        self.setFixedSize(ancho, alto)
        self.botones_tab["pend"].setChecked(self.tab == "pend")
        for c, b in self.botones_tab.items():
            b.setChecked(c == self.tab)

    # ------------------------------------------------------------------ posicion
    def _pantalla(self):
        g = self.screen().availableGeometry()
        return (g.x(), g.y(), g.width(), g.height())

    def _colocar_inicial(self):
        pos = self.ajustes["pos"]
        w, h = self._tam_icono()
        if pos and QGuiApplication.screenAt(QPoint(pos[0] + 10, pos[1] + 10)) is not None:
            x, y = geometria.dentro((pos[0], pos[1]), (w, h), self._pantalla())
        else:
            g = self.screen().availableGeometry()
            x, y = g.left() + 20, g.bottom() - h - 20
        self.move(x, y)

    def _guardar_pos(self):
        if self.expandido:
            x, y = geometria.contraer((self.x(), self.y(), self.width(), self.height()), self.ancla, self._tam_icono())
        else:
            x, y = self.x(), self.y()
        self.ajustes["pos"] = [x, y]
        self.ajustes.guardar()

    def expandir(self):
        if self.expandido:
            return
        icono = (self.x(), self.y(), self.width(), self.height())
        rect, self.ancla = geometria.expandir(icono, self._tam_panel(), self._pantalla())
        self.expandido = True
        self.panel.setVisible(True)
        self.setFixedSize(rect[2], rect[3])
        self.move(rect[0], rect[1])
        self.reconstruir()
        self._opacidad()
        self.update()

    def contraer(self):
        if not self.expandido:
            return
        x, y = geometria.contraer((self.x(), self.y(), self.width(), self.height()), self.ancla, self._tam_icono())
        self.expandido = False
        self.panel.setVisible(False)
        self.setFixedSize(*self._tam_icono())
        self.move(x, y)
        self._guardar_pos()
        self._opacidad()
        self.update()

    # ------------------------------------------------------------------ pintura
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        urg = self._hay_urgente()
        if not self.expandido:
            pad, d = self.px(7), self.px(60)
            base = (URG_A if self._parpadeo else URG_B) if urg else (VERDE if self.n_activos == 0 else QColor(self.ajustes["color_icono"]))
            sombra = QColor(0, 0, 0, 60)
            p.setPen(Qt.NoPen)
            p.setBrush(sombra)
            p.drawEllipse(pad, pad + self.px(2), d, d)
            p.setBrush(base)
            p.drawEllipse(pad, pad, d, d)
            iconos.dibujar(p, self.ajustes["dibujo_icono"], pad, pad, d, base)
            if self.n_activos > 0:
                r = self.px(12)
                cx, cy = pad + d - r * 0.55, pad + r * 0.55
                p.setPen(QPen(QColor("white"), self.px(2)))
                p.setBrush(QColor("#ef4444"))
                p.drawEllipse(QPointF(cx, cy), r, r)
                p.setPen(QColor("white"))
                f = QFont("Segoe UI", 1)
                f.setPixelSize(self.px(12 if self.n_activos < 10 else 10))
                f.setBold(True)
                p.setFont(f)
                p.drawText(QRectF(cx - r, cy - r, 2 * r, 2 * r), Qt.AlignCenter, str(self.n_activos) if self.n_activos < 100 else "99+")
        else:
            fondo = QColor(self.ajustes["color_fondo"])
            fondo.setAlpha(245)
            p.setBrush(fondo)
            p.setPen(QPen(URG_A if (urg and self._parpadeo) else QColor(255, 255, 255, 30), self.px(2) if urg else 1))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), self.px(16), self.px(16))

    def _alternar(self):
        self._parpadeo = not self._parpadeo
        self.update()

    # ------------------------------------------------------------------ raton
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._arrastre = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._movido = False
            self._clic_en_cabecera = e.position().y() < self.px(62)
            self._opacidad()

    def mouseMoveEvent(self, e):
        if self._arrastre is not None and e.buttons() & Qt.LeftButton:
            destino = e.globalPosition().toPoint() - self._arrastre
            if (destino - self.frameGeometry().topLeft()).manhattanLength() > 4:
                self._movido = True
            self.move(destino)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or self._arrastre is None:
            return
        self._arrastre = None
        if self._movido:
            if not self.expandido:
                x, y = geometria.pegar_a_borde((self.x(), self.y()), (self.width(), self.height()), self._pantalla())
                self.move(x, y)
            self._guardar_pos()
        elif not self.expandido:
            self.expandir()
        elif self._clic_en_cabecera:
            self.contraer()
        self._opacidad()

    def enterEvent(self, _):
        self._hover = True
        self.t_leave.stop()
        self._opacidad()

    def leaveEvent(self, _):
        self.t_leave.start()

    def _salio(self):
        self._hover = self.underMouse()
        self._opacidad()

    def _opacidad(self):
        if self._hay_urgente() or self._hover or self._arrastre is not None or QApplication.activePopupWidget():
            o = 1.0
        else:
            o = 0.85 if self.expandido else 0.5
        self.setWindowOpacity(o)

    # ------------------------------------------------------------------ calculos
    def _activas(self) -> List[Pendiente]:
        return [p for p in self.pendientes if not self.tareas.hecha(p.id)]

    def _hay_urgente(self) -> bool:
        ahora = datetime.now(timezone.utc)
        return any(0 < (p.vence - ahora).total_seconds() < 3600 and p.entregada is not True
                   and not self.tareas.hecha(p.id) and not self.tareas.silenciada(p.id) for p in self.pendientes)

    def _estadisticas(self):
        return resumen.estadisticas(self.pendientes, self.tareas.hecha, self.res.entregadas_semana, datetime.now(timezone.utc))

    # ------------------------------------------------------------------ contenido
    def cambiar_tab(self, clave: str):
        self.tab = clave
        self.reconstruir()

    def _limpiar(self):
        while self.lista_lay.count():
            it = self.lista_lay.takeAt(0)
            w = it.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def _titulo_seccion(self, texto: str):
        l = QLabel(texto.upper())
        l.setStyleSheet(f"color:{TEXTO2};font-size:{self.px(10)}px;font-weight:700;letter-spacing:1px;padding-top:{self.px(6)}px;")
        self.lista_lay.addWidget(l)

    def _vacio(self, texto: str):
        l = QLabel(texto)
        l.setWordWrap(True)
        l.setAlignment(Qt.AlignCenter)
        l.setStyleSheet(f"color:{TEXTO2};padding:{self.px(24)}px;")
        self.lista_lay.addWidget(l)

    def reconstruir(self):
        if not self.expandido:
            return
        est = self._estadisticas()
        no_vistos = [a for a in self.res.anuncios if a.id not in self.ajustes["anuncios_vistos"]]
        textos = {"pend": f"Pendientes {len(est['activos'])}", "cursos": f"Cursos {len(self.res.cursos)}",
                  "anuncios": "Anuncios" + (f" ●{len(no_vistos)}" if no_vistos else ""), "notas": "Notas"}
        for c, b in self.botones_tab.items():
            b.setText(textos[c])
            b.setChecked(c == self.tab)
        self._limpiar()
        ahora = datetime.now(timezone.utc)
        {"pend": self._tab_pendientes, "cursos": self._tab_cursos,
         "anuncios": self._tab_anuncios, "notas": self._tab_notas}[self.tab](ahora)
        self.lista_lay.addStretch(1)
        self.actualizar_cabecera()

    def actualizar_cabecera(self):
        est = self._estadisticas()
        self.l_titulo.setText(self.res.termino or "Mis pendientes")
        hoy = len(est["hoy"])
        self.l_resumen.setText(f"Hoy vence{'n' if hoy != 1 else ''} {hoy} · Esta semana faltan {est['semana_faltan']} de {est['semana_total']}"
                               if est["semana_total"] else f"Hoy vence{'n' if hoy != 1 else ''} {hoy} · Sin entregas esta semana")
        self.barra.setMaximum(max(1, est["semana_total"]))
        self.barra.setValue(est["semana_hechas"])

    # --- pestana Pendientes ---
    def _grupo(self, p: Pendiente, ahora: datetime) -> str:
        if self.tareas.hecha(p.id):
            return "Hechas"
        if p.vence < ahora:
            return "Vencidas"
        hoy = ahora.astimezone(ZONA).date()
        d = p.vence.astimezone(ZONA).date()
        if d == hoy:
            return "Hoy"
        if d == hoy + timedelta(days=1):
            return "Mañana"
        domingo = resumen.limites_semana(ahora)[1]
        if d <= domingo:
            return "Esta semana"
        return "Próxima semana"

    def _tab_pendientes(self, ahora):
        lista = [p for p in self.pendientes if not self.filtro_curso or p.materia == self.filtro_curso]
        if self.filtro_curso:
            chip = QPushButton(f"Solo: {self.filtro_curso}   ✕")
            chip.setCursor(Qt.PointingHandCursor)
            chip.setStyleSheet(f"QPushButton{{color:white;background:{self.ajustes['color_icono']};border:none;border-radius:{self.px(10)}px;"
                               f"padding:{self.px(5)}px {self.px(10)}px;font-size:{self.px(11)}px;text-align:left;}}")
            chip.clicked.connect(self._quitar_filtro)
            self.lista_lay.addWidget(chip)
        if not lista:
            self._vacio("No tienes pendientes en los próximos 7 días 🎉" if not self.filtro_curso else "Este curso no tiene pendientes 🎉")
            return
        orden = ["Vencidas", "Hoy", "Mañana", "Esta semana", "Próxima semana", "Hechas"]
        por_grupo = {g: [] for g in orden}
        for p in lista:
            por_grupo[self._grupo(p, ahora)].append(p)
        for g in orden:
            if por_grupo[g]:
                self._titulo_seccion(f"{g} ({len(por_grupo[g])})")
                for p in por_grupo[g]:
                    self.lista_lay.addWidget(self._fila_tarea(p, ahora))

    def _quitar_filtro(self):
        self.filtro_curso = None
        self.reconstruir()

    def _fila_tarea(self, p: Pendiente, ahora: datetime) -> QWidget:
        px = self.px
        hecha, silen = self.tareas.hecha(p.id), self.tareas.silenciada(p.id)
        horas = (p.vence - ahora).total_seconds() / 3600
        borde = "#6b7280" if hecha else "#ef4444" if horas < 1 else "#f59e0b" if horas < 24 else "#3b82f6"
        f = Tarjeta(self.k, borde)
        h = QHBoxLayout(f)
        h.setContentsMargins(px(8), px(6), px(6), px(6))
        c = QCheckBox()
        c.setChecked(hecha)
        c.setCursor(Qt.PointingHandCursor)
        c.setToolTip("Marcar como hecha (solo en este widget)")
        c.setStyleSheet(f"QCheckBox::indicator{{width:{px(18)}px;height:{px(18)}px;border-radius:{px(9)}px;border:2px solid #6b7280;}}"
                        "QCheckBox::indicator:checked{background:#10b981;border-color:#10b981;}")
        c.toggled.connect(lambda v, pid=p.id: self.marcar_hecha(pid, v))
        h.addWidget(c)
        mat = f"{p.materia} · " if p.materia else ""
        extra = ""
        if silen:
            extra += " · 🔕 silenciada"
        ph = self.tareas.posponer_hasta(p.id)
        if ph:
            extra += f" · ⏰ {ph.astimezone(ZONA).strftime('%I:%M %p').lstrip('0')}"
        if self.tareas.repetir_min(p.id):
            extra += f" · 🔁 cada {_nombre_intervalo(self.tareas.repetir_min(p.id))}"
        titulo = _esc(p.titulo)
        if hecha:
            titulo = f"<s>{titulo}</s>"
        color = "#6b7280" if hecha else "#fca5a5" if horas < 1 else "#fcd34d" if horas < 24 else "#d1d5db"
        et = Clicable()
        et.setTextFormat(Qt.RichText)
        et.setWordWrap(True)
        et.setCursor(Qt.PointingHandCursor)
        et.setText(f"<div style='font-weight:600;color:{'#9ca3af' if hecha else 'white'}'>{titulo}</div>"
                   f"<div style='color:{color};font-size:{px(11)}px'>{_esc(mat)}{formato.fecha_hora(p.vence)} · {formato.cuenta(p.vence - ahora)}{extra}</div>")
        et.clic.connect(lambda url=p.url: QDesktopServices.openUrl(QUrl(url)) if url else None)
        h.addWidget(et, 1)
        b = QToolButton()
        b.setText("⏰")
        b.setToolTip("Posponer, repetir o silenciar")
        b.setFixedSize(px(28), px(28))
        b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet("QToolButton{background:rgba(255,255,255,0.08);border:none;border-radius:6px;color:white;}"
                        "QToolButton:hover{background:rgba(255,255,255,0.22);}")
        b.clicked.connect(lambda _=False, pp=p, bb=b: self.menu_tarea(pp, bb))
        h.addWidget(b)
        return f

    # --- pestana Cursos ---
    def _tab_cursos(self, ahora):
        if not self.res.cursos:
            self._vacio("Aún no hay cursos. Presiona «Actualizar ahora».")
            return
        activas = self._activas()
        filas = []
        for cu in self.res.cursos:
            propios = [p for p in activas if p.materia == cu.nombre]
            filas.append((cu, propios))
        filas.sort(key=lambda x: (-len(x[1]), x[0].nombre))
        self._titulo_seccion(f"{self.res.termino or 'Periodo actual'} · {len(filas)} cursos")
        for cu, propios in filas:
            urgente = any((p.vence - ahora).total_seconds() < 86400 for p in propios)
            borde = "#ef4444" if urgente else "#f59e0b" if propios else "#10b981"
            f = Tarjeta(self.k, borde)
            h = QHBoxLayout(f)
            h.setContentsMargins(self.px(10), self.px(8), self.px(10), self.px(8))
            et = Clicable()
            et.setWordWrap(True)
            et.setTextFormat(Qt.RichText)
            et.setCursor(Qt.PointingHandCursor)
            n = len(propios)
            estado = "✓ Sin pendientes" if n == 0 else f"{n} pendiente{'s' if n != 1 else ''}"
            hoy = sum(1 for p in propios if p.vence.astimezone(ZONA).date() == ahora.astimezone(ZONA).date())
            if hoy:
                estado += f" · {hoy} vence{'n' if hoy != 1 else ''} hoy"
            col = "#fca5a5" if urgente else "#fcd34d" if n else "#6ee7b7"
            et.setText(f"<div style='font-weight:600'>{_esc(cu.nombre)}</div><div style='color:{col};font-size:{self.px(11)}px'>{estado}</div>")
            et.clic.connect(lambda nombre=cu.nombre: self._filtrar_curso(nombre))
            h.addWidget(et, 1)
            if cu.promedio is not None:
                pr = QLabel(f"<div style='font-size:{self.px(15)}px;font-weight:700'>{cu.promedio:g}%</div>"
                            f"<div style='color:{TEXTO2};font-size:{self.px(9)}px' align='right'>promedio</div>")
                pr.setTextFormat(Qt.RichText)
                pr.setAlignment(Qt.AlignRight)
                h.addWidget(pr)
            self.lista_lay.addWidget(f)

    def _filtrar_curso(self, nombre: str):
        self.filtro_curso = nombre
        self.tab = "pend"
        self.reconstruir()

    # --- pestana Anuncios ---
    def _tab_anuncios(self, ahora):
        if not self.res.anuncios:
            self._vacio("No hay anuncios recientes de tus docentes.")
            return
        vistos = set(self.ajustes["anuncios_vistos"])
        for a in self.res.anuncios:
            nuevo = a.id not in vistos
            f = Tarjeta(self.k, "#3b82f6" if nuevo else "transparent")
            h = QVBoxLayout(f)
            h.setContentsMargins(self.px(10), self.px(8), self.px(10), self.px(8))
            et = Clicable()
            et.setWordWrap(True)
            et.setTextFormat(Qt.RichText)
            et.setCursor(Qt.PointingHandCursor)
            punto = "<span style='color:#60a5fa'>● </span>" if nuevo else ""
            meta = " · ".join(x for x in (a.materia, hace(a.fecha)) if x)
            et.setText(f"<div style='font-weight:600'>{punto}{_esc(a.titulo)}</div>"
                       f"<div style='color:{TEXTO2};font-size:{self.px(11)}px'>{_esc(meta)}</div>"
                       f"<div style='color:#d1d5db;font-size:{self.px(11)}px'>{_esc(a.texto)}</div>")
            et.clic.connect(lambda url=a.url: QDesktopServices.openUrl(QUrl(url)) if url else None)
            h.addWidget(et)
            self.lista_lay.addWidget(f)
        # al abrir la pestana se consideran vistos
        self.ajustes["anuncios_vistos"] = list(vistos | {a.id for a in self.res.anuncios})
        self.ajustes.guardar()

    # --- pestana Notas ---
    def _tab_notas(self, ahora):
        con_prom = [c for c in self.res.cursos if c.promedio is not None]
        if con_prom:
            self._titulo_seccion("Promedio por curso")
            f = Tarjeta(self.k)
            v = QVBoxLayout(f)
            v.setContentsMargins(self.px(10), self.px(6), self.px(10), self.px(6))
            for c in sorted(con_prom, key=lambda c: c.nombre):
                l = QLabel(f"{_esc(c.nombre)}<span style='float:right'> <b>{c.promedio:g}%</b></span>")
                l.setTextFormat(Qt.RichText)
                l.setWordWrap(True)
                v.addWidget(l)
            self.lista_lay.addWidget(f)
        self._titulo_seccion("Últimas calificaciones")
        if not self.res.notas:
            self._vacio("Todavía no hay calificaciones recientes.")
            return
        for n in self.res.notas:
            f = Tarjeta(self.k, "#10b981")
            h = QHBoxLayout(f)
            h.setContentsMargins(self.px(10), self.px(8), self.px(10), self.px(8))
            et = Clicable()
            et.setWordWrap(True)
            et.setTextFormat(Qt.RichText)
            et.setCursor(Qt.PointingHandCursor)
            meta = " · ".join(x for x in (n.materia, hace(n.fecha)) if x)
            et.setText(f"<div style='font-weight:600'>{_esc(n.titulo)}</div><div style='color:{TEXTO2};font-size:{self.px(11)}px'>{_esc(meta)}</div>")
            et.clic.connect(lambda url=n.url: QDesktopServices.openUrl(QUrl(url)) if url else None)
            h.addWidget(et, 1)
            nota = QLabel(f"<b style='font-size:{self.px(15)}px'>{_esc(n.texto)}</b>")
            nota.setTextFormat(Qt.RichText)
            h.addWidget(nota)
            self.lista_lay.addWidget(f)

    # ------------------------------------------------------------------ acciones por tarea
    def _accion(self, menu: QMenu, texto: str, fn):
        a = QAction(texto, menu)
        a.triggered.connect(lambda _=False: fn())
        menu.addAction(a)

    def menu_tarea(self, p: Pendiente, boton: QWidget):
        m = QMenu(self)
        sub = m.addMenu("Recordarme en…")
        for texto, mins in (("30 minutos", 30), ("1 hora", 60), ("3 horas", 180)):
            self._accion(sub, texto, lambda mins=mins: self.posponer(p, mins))
        self._accion(sub, "Mañana a las 8:00 AM", lambda: self.posponer_manana(p))
        sub2 = m.addMenu("Recordarme cada…")
        for texto, mins in (("1 hora", 60), ("3 horas", 180), ("6 horas", 360), ("día", 1440)):
            self._accion(sub2, texto, lambda mins=mins: self.repetir(p, mins))
        if self.tareas.repetir_min(p.id):
            self._accion(m, "Dejar de repetir", lambda: self.repetir(p, 0))
        if self.tareas.posponer_hasta(p.id):
            self._accion(m, "Cancelar recordatorio programado", lambda: self._cancelar_pospuesta(p))
        m.addSeparator()
        if self.tareas.silenciada(p.id):
            self._accion(m, "Reactivar avisos de esta tarea", lambda: self.silenciar(p, False))
        else:
            self._accion(m, "Silenciar avisos de esta tarea", lambda: self.silenciar(p, True))
        hecha = self.tareas.hecha(p.id)
        self._accion(m, "Marcar como pendiente" if hecha else "Marcar como hecha", lambda: self.marcar_hecha(p.id, not hecha))
        self._accion(m, "Abrir en Canvas", lambda: QDesktopServices.openUrl(QUrl(p.url)))
        m.exec(boton.mapToGlobal(boton.rect().bottomLeft()))

    def _aviso(self, texto: str):
        self.l_estado.setText(texto)
        self.reconstruir()
        self.cada_segundo()

    def posponer(self, p: Pendiente, minutos: int):
        hasta = datetime.now(timezone.utc) + timedelta(minutes=minutos)
        self.tareas.posponer(p.id, hasta)
        self._aviso(f"Te recordaré de «{p.titulo}» a las {hasta.astimezone(ZONA).strftime('%I:%M %p').lstrip('0')}.")

    def posponer_manana(self, p: Pendiente):
        man = (datetime.now(ZONA) + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        self.tareas.posponer(p.id, man)
        self._aviso(f"Te recordaré de «{p.titulo}» mañana a las 8:00 AM.")

    def _cancelar_pospuesta(self, p: Pendiente):
        self.tareas._set(p.id, posponer_hasta=None)
        self._aviso("Recordatorio cancelado.")

    def repetir(self, p: Pendiente, minutos: int):
        self.tareas.repetir(p.id, minutos, datetime.now(timezone.utc))
        self._aviso(f"Te recordaré de «{p.titulo}» cada {_nombre_intervalo(minutos)}." if minutos else "Listo, ya no se repetirá.")

    def silenciar(self, p: Pendiente, valor: bool):
        self.tareas.silenciar(p.id, valor)
        self._aviso("Avisos silenciados para esa tarea." if valor else "Avisos reactivados para esa tarea.")

    def marcar_hecha(self, id_: str, valor: bool):
        self.tareas.marcar_hecha(id_, valor)
        QTimer.singleShot(0, lambda: (self.reconstruir(), self.cada_segundo(), self.update()))

    # ------------------------------------------------------------------ ciclo
    def cada_segundo(self):
        ahora = datetime.now(timezone.utc)
        activas = self._activas()
        n = len(activas)
        if n != self.n_activos:
            self.n_activos = n
            self.update()
        futuras = [p for p in activas if p.vence >= ahora]
        tip = f"{n} pendiente{'s' if n != 1 else ''}"
        if futuras:
            p = futuras[0]
            tip += f"\nPróxima: {p.titulo} · {formato.cuenta(p.vence - ahora, (p.vence - ahora).total_seconds() < 3600)}"
        self.setToolTip(tip)
        urg = self._hay_urgente()
        if urg and not self.t_parpadeo.isActive():
            self.t_parpadeo.start()
            self._opacidad()
        elif not urg and self.t_parpadeo.isActive():
            self.t_parpadeo.stop()
            self._opacidad()
            self.update()
        for a in list(self._alertas):
            a.actualizar() if a.isVisible() else self._alertas.remove(a)
        if self.expandido:
            self.actualizar_cabecera()
            if int(ahora.timestamp()) % 60 == 0 and not QApplication.activePopupWidget():
                self.reconstruir()

    def revisar_programados(self):
        if not self.pendientes:
            return
        ahora = datetime.now(timezone.utc)
        enviados = self.tareas.avisos_programados(self.pendientes, ahora)
        for p, motivo in enviados:
            mat = f" · {p.materia}" if p.materia else ""
            self.notificador.enviar("Recordatorio" if motivo == "repeticion" else "Recordatorio que programaste",
                                    f"{p.titulo}{mat} — entrega {formato.cuenta(p.vence - ahora)}", p.url)
        if enviados and self.expandido and not QApplication.activePopupWidget():
            self.reconstruir()

    # --- resumen ---
    def enviar_resumen(self):
        titulo, msg = resumen.texto_resumen(self._estadisticas())
        self.notificador.enviar(titulo, msg)

    def revisar_resumen(self):
        if not self.ajustes["resumen_activo"] or self.res.actualizado is None:
            return
        ahora = datetime.now(ZONA)
        hoy = ahora.date().isoformat()
        try:
            hh, mm = (int(x) for x in self.ajustes["hora_resumen"].split(":"))
        except ValueError:
            hh, mm = 8, 0
        if self.ajustes["ultimo_resumen"] != hoy and (ahora.hour, ahora.minute) >= (hh, mm):
            self.ajustes["ultimo_resumen"] = hoy
            self.ajustes.guardar()
            self.enviar_resumen()

    # --- datos nuevos ---
    def actualizar_ahora(self):
        if self.trabajador.lanzar():
            self.l_estado.setText("Actualizando…")

    def probar_notificacion(self):
        self.notificador.enviar("College Widget", "Esta es una notificación de prueba. ¡Funciona!")

    def abrir_conexion(self):
        if DialogoConexion(self, self.ajustes).exec():
            self.actualizar_ahora()

    def abrir_ajustes(self):
        antes = self.k
        if DialogoAjustes(self.ajustes, self).exec():
            if self.k != antes:
                self._construir()
                self.reconstruir()
            self.update()
            self._opacidad()

    def al_terminar(self, res: Resultado, notificar: bool = True):
        self.res = res
        self.pendientes = res.pendientes
        hora = res.actualizado.astimezone(ZONA).strftime("%I:%M %p").lstrip("0") if res.actualizado else "—"
        if res.sin_credenciales:
            self.l_estado.setText("Aún no estás conectado a tu plataforma. Presiona «Conexión…».")
        elif res.sin_conexion:
            self.l_estado.setText(f"Sin internet. Mostrando los últimos datos guardados (de las {hora}).")
        elif res.error:
            self.l_estado.setText(res.error)
        else:
            self.l_estado.setText(f"Actualizado a las {hora}" + (" (calendario iCal)" if res.fuente == "ical" else ""))
            self.tareas.limpiar({p.id for p in res.pendientes})
        if notificar:
            for a in res.avisos:
                self.notificador.enviar(a.titulo, a.mensaje, a.url)
            for r in res.recordatorios:
                self.notificador.enviar(r.titulo, r.mensaje, r.pendiente.url)
                if r.nivel == "1h":
                    self._alerta_urgente(r.pendiente)
        if res.sin_conexion and not self._reintento:  # al encender la PC el internet puede tardar
            self._reintento = True
            QTimer.singleShot(30_000, self._reintentar)
        self.reconstruir()
        self.cada_segundo()
        self.update()
        if res.sin_credenciales and notificar and not self._pidio_conexion:
            self._pidio_conexion = True
            self.setVisible(True)
            self.abrir_conexion()

    def _reintentar(self):
        self._reintento = False
        self.actualizar_ahora()

    def _alerta_urgente(self, p: Pendiente):
        if self.tareas.silenciada(p.id) or self.tareas.hecha(p.id):
            return
        clave = (p.id, p.vence.isoformat())
        if clave in self._alertados:
            return
        self._alertados.add(clave)
        a = AlertaUrgente(p, desplazamiento=30 * len(self._alertas))
        self._alertas.append(a)
        a.show()
        a.raise_()
        a.activateWindow()


def _nombre_intervalo(minutos: int) -> str:
    if minutos >= 1440:
        return "día"
    if minutos % 60 == 0:
        h = minutos // 60
        return "hora" if h == 1 else f"{h} horas"
    return f"{minutos} min"
