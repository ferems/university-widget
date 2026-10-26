from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import QTime, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QTimeEdit, QVBoxLayout)

from . import credenciales, formato, iconos, inicio_auto
from .config import FUENTE
from .ajustes import ESCALAS, FONDOS, ICONOS, Ajustes, normalizar_url, url_canvas, url_moodle
from .plataformas import GUIAS_ICAL
from .modelos import Pendiente

AYUDA = {
    "canvas": ("En Canvas (en el navegador): foto de perfil → Configuración → baja hasta «Integraciones aprobadas» "
               "→ «+ Nuevo token de acceso». Ponle un nombre, deja la fecha de vencimiento vacía y copia el "
               "token que aparece (solo se muestra una vez). Muestra tareas, cursos, promedios, notas y anuncios."),
    "moodle": ("Escribe la dirección de tu Moodle (la que usas para entrar). Luego, en Moodle: tu foto de perfil → "
               "Preferencias → Cuenta de usuario → «Claves de seguridad» → copia la clave de «Moodle mobile web service». "
               "Muestra tareas (y si ya entregaste), cursos, promedios, notas y anuncios. Si no ves esa clave, tu "
               "universidad no la activó: usa «Otra plataforma»."),
    "ical": ("Para Google Classroom, Blackboard, Brightspace, Schoology, Teams y cualquier otra. Solo se leen las fechas del "
             "calendario: no hay notas, promedios ni anuncios, ni se sabe si ya entregaste. Elige tu plataforma "
             "para ver dónde sacar el enlace:"),
}
NOMBRES = {"canvas": "Canvas — token de acceso (recomendado)", "moodle": "Moodle — token de acceso",
           "ical": "Otra plataforma — enlace de calendario (iCal)"}
CREDENCIAL = {"canvas": credenciales.TOKEN, "moodle": credenciales.MOODLE, "ical": credenciales.ICAL}


class DialogoConexion(QDialog):
    """Elige la plataforma y guarda el token / enlace en el llavero seguro del sistema (Windows o Mac)."""

    def __init__(self, padre=None, ajustes: Ajustes | None = None):
        super().__init__(padre)
        self.a = ajustes or Ajustes()
        self.setWindowTitle("Conectar con tu plataforma")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setFixedWidth(580)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("¿Cómo quieres conectarte?"))
        self.tipo = QComboBox()
        for k, nombre in NOMBRES.items():
            self.tipo.addItem(nombre, k)
        actual = self.a["plataforma"]
        if actual in NOMBRES:
            self.tipo.setCurrentIndex(list(NOMBRES).index(actual))
        self.tipo.currentIndexChanged.connect(self._cambio)
        lay.addWidget(self.tipo)
        self.ayuda = QLabel()
        self.ayuda.setWordWrap(True)
        lay.addWidget(self.ayuda)
        self.guia_combo = QComboBox()
        self.guia_combo.addItems([n for n in GUIAS_ICAL if n != "Canvas"])
        self.guia_combo.currentIndexChanged.connect(self._guia)
        lay.addWidget(self.guia_combo)
        self.guia = QLabel()
        self.guia.setWordWrap(True)
        self.guia.setFixedWidth(556)
        lay.addWidget(self.guia)

        self.l_sitio = QLabel()
        self.sitio = QLineEdit()
        lay.addWidget(self.l_sitio)
        lay.addWidget(self.sitio)

        self.caja = QLineEdit()
        self.caja.setEchoMode(QLineEdit.Password)
        lay.addWidget(self.caja)
        self.estado = QLabel("")
        self.estado.setWordWrap(True)
        lay.addWidget(self.estado)
        fila = QHBoxLayout()
        self.b_guardar = QPushButton("Guardar")
        self.b_guardar.clicked.connect(self._guardar)
        b_cerrar = QPushButton("Cancelar")
        b_cerrar.clicked.connect(self.reject)
        fila.addStretch(1)
        fila.addWidget(b_cerrar)
        fila.addWidget(self.b_guardar)
        lay.addLayout(fila)
        self._cambio()

    def _guia(self):
        self.guia.setText(GUIAS_ICAL.get(self.guia_combo.currentText(), ""))
        self.guia.setMinimumHeight(self.guia.heightForWidth(556))
        self.layout().activate()
        self.adjustSize()

    def _cambio(self):
        k = self.tipo.currentData()
        self.ayuda.setText(AYUDA[k])
        self.ayuda.setFixedWidth(556)  # asi Qt calcula bien cuantas lineas ocupa el texto
        self.ayuda.setMinimumHeight(self.ayuda.heightForWidth(556))
        con_sitio = k in ("canvas", "moodle")
        self.l_sitio.setVisible(con_sitio)
        self.sitio.setVisible(con_sitio)
        self.guia_combo.setVisible(k == "ical")
        self.guia.setVisible(k == "ical")
        if k == "canvas":
            self.l_sitio.setText("Dirección de tu Canvas:")
            self.sitio.setText(url_canvas())
            self.sitio.setPlaceholderText("https://tu-universidad.instructure.com")
        elif k == "moodle":
            self.l_sitio.setText("Dirección de tu Moodle:")
            self.sitio.setText(url_moodle())
            self.sitio.setPlaceholderText("https://campus.tu-universidad.edu.hn")
        self.caja.setPlaceholderText("Pega aquí el enlace (se verá oculto)" if k == "ical" else "Pega aquí el token (se verá oculto)")
        guardado = credenciales.obtener(CREDENCIAL[k]) is not None
        self.estado.setStyleSheet("")
        self.estado.setText("Ya hay uno guardado (no se muestra). Si pegas otro, lo reemplaza." if guardado else "")
        self._guia()

    def _error(self, texto):
        self.estado.setStyleSheet("color:#b91c1c;")
        self.estado.setText(texto)

    def _guardar(self):
        k = self.tipo.currentData()
        valor = self.caja.text().strip()
        if not valor:
            self._error("Pega primero el valor.")
            return
        try:
            if k == "canvas":
                self.a["url_canvas"] = normalizar_url(self.sitio.text())
            elif k == "moodle":
                self.a["url_moodle"] = normalizar_url(self.sitio.text(), True, "Moodle")
        except ValueError as e:
            self._error(str(e))
            return
        if k == "ical" and not valor.lower().startswith(("https://", "http://", "webcal://")):
            self._error("El enlace de calendario debe empezar con https:// o webcal://")
            return
        try:
            credenciales.guardar(CREDENCIAL[k], valor)
            self.a["plataforma"] = k
            self.a.guardar()
        except Exception as e:
            self._error(f"No se pudo guardar en el Administrador de credenciales: {type(e).__name__}")
            return
        self.caja.clear()
        self.accept()


class AlertaUrgente(QDialog):
    """Ventana grande encima de todo cuando falta menos de 1 hora."""

    def __init__(self, p: Pendiente, desplazamiento: int = 0):
        super().__init__(None)
        self.p = p
        self.setWindowTitle("¡Entrega urgente!")
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setStyleSheet("QDialog{background:#7f1d1d;} QLabel{color:white;} "
                           "QPushButton{font-size:16px;padding:10px 20px;border-radius:8px;background:white;color:#7f1d1d;font-weight:bold;}")
        self.resize(620, 320)
        lay = QVBoxLayout(self)
        t = QLabel("⚠ ENTREGA EN MENOS DE 1 HORA")
        t.setFont(QFont(FUENTE, 20, QFont.Bold))
        lay.addWidget(t)
        n = QLabel(p.titulo)
        n.setFont(QFont(FUENTE, 26, QFont.Bold))
        n.setWordWrap(True)
        lay.addWidget(n, 1)
        self.info = QLabel()
        self.info.setFont(QFont(FUENTE, 15))
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        fila = QHBoxLayout()
        b1 = QPushButton("Abrir en Canvas")
        b1.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(p.url)))
        b2 = QPushButton("Entendido")
        b2.clicked.connect(self.close)
        fila.addWidget(b1)
        fila.addStretch(1)
        fila.addWidget(b2)
        lay.addLayout(fila)
        self.actualizar()
        pantalla = self.screen().availableGeometry()
        self.move(pantalla.center().x() - 310 + desplazamiento, pantalla.center().y() - 160 + desplazamiento)

    def actualizar(self):
        ahora = datetime.now(timezone.utc)
        mat = f"{self.p.materia} · " if self.p.materia else ""
        self.info.setText(f"{mat}{formato.fecha_hora(self.p.vence)}  —  {formato.cuenta(self.p.vence - ahora, True)}")


class DialogoAjustes(QDialog):
    """Tamano, inicio automatico y resumen diario."""

    def __init__(self, ajustes: Ajustes, padre=None):
        super().__init__(padre)
        self.a = ajustes
        self.setWindowTitle("Ajustes")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)

        fila = QHBoxLayout()
        fila.addWidget(QLabel("Tamaño del widget:"))
        self.c_tam = QComboBox()
        for nombre in ESCALAS:
            self.c_tam.addItem(nombre)
        actual = min(ESCALAS, key=lambda n: abs(ESCALAS[n] - float(ajustes["escala"])))
        self.c_tam.setCurrentText(actual)
        fila.addWidget(self.c_tam, 1)
        lay.addLayout(fila)

        self.c_inicio = QCheckBox("Abrir el widget automáticamente al iniciar sesión en la computadora")
        self.inicio_antes = inicio_auto.activo()
        self.c_inicio.setChecked(self.inicio_antes)
        if not inicio_auto.disponible():
            self.c_inicio.setEnabled(False)
            self.c_inicio.setToolTip("Solo funciona en Windows y Mac")
        lay.addWidget(self.c_inicio)

        self.c_resumen = QCheckBox("Enviarme un resumen diario (hoy y esta semana) a las:")
        self.c_resumen.setChecked(bool(ajustes["resumen_activo"]))
        lay.addWidget(self.c_resumen)
        self.hora = QTimeEdit(QTime.fromString(ajustes["hora_resumen"], "HH:mm"))
        self.hora.setDisplayFormat("hh:mm AP")
        lay.addWidget(self.hora)

        self.color_fondo = ajustes["color_fondo"]
        self.color_icono = ajustes["color_icono"]
        self.muestra_fondo = self._fila_colores(lay, "Color de fondo del panel:", FONDOS, "fondo")
        self.muestra_icono = self._fila_colores(lay, "Color del ícono:", ICONOS, "icono")

        lay.addWidget(QLabel("Dibujo del ícono (cuando está contraído):"))
        self.dibujo = ajustes["dibujo_icono"]
        fila_d = QHBoxLayout()
        fila_d.setSpacing(6)
        self.botones_dibujo = {}
        for clave, nombre in iconos.DIBUJOS:
            b = QPushButton()
            b.setCheckable(True)
            b.setFixedSize(52, 52)
            b.setIconSize(b.size() * 0.8)
            b.setToolTip(nombre)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("QPushButton{border:2px solid transparent;border-radius:12px;background:transparent;}"
                            "QPushButton:checked{border-color:#111827;background:rgba(0,0,0,0.08);}"
                            "QPushButton:hover{background:rgba(0,0,0,0.06);}")
            b.clicked.connect(lambda _=False, c=clave: self._poner_dibujo(c))
            self.botones_dibujo[clave] = b
            fila_d.addWidget(b)
        fila_d.addStretch(1)
        lay.addLayout(fila_d)
        self._refrescar_dibujos()

        self.estado = QLabel("")
        self.estado.setWordWrap(True)
        self.estado.setStyleSheet("color:#b91c1c;")
        lay.addWidget(self.estado)
        fila2 = QHBoxLayout()
        fila2.addStretch(1)
        b0 = QPushButton("Cancelar")
        b0.clicked.connect(self.reject)
        b1 = QPushButton("Guardar")
        b1.clicked.connect(self._guardar)
        fila2.addWidget(b0)
        fila2.addWidget(b1)
        lay.addLayout(fila2)

    def _fila_colores(self, lay, titulo, opciones, cual):
        lay.addWidget(QLabel(titulo))
        fila = QHBoxLayout()
        fila.setSpacing(6)
        for nombre, hexa in opciones:
            b = QPushButton()
            b.setFixedSize(30, 30)
            b.setToolTip(nombre)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(f"QPushButton{{background:{hexa};border:2px solid #9ca3af;border-radius:15px;}}"
                            "QPushButton:hover{border-color:#111827;}")
            b.clicked.connect(lambda _=False, h=hexa: self._poner_color(cual, h))
            fila.addWidget(b)
        otro = QPushButton("Otro…")
        otro.clicked.connect(lambda: self._elegir(cual))
        fila.addWidget(otro)
        muestra = QLabel("  actual  ")
        fila.addWidget(muestra)
        fila.addStretch(1)
        lay.addLayout(fila)
        self._pintar_muestra(muestra, self.color_fondo if cual == "fondo" else self.color_icono)
        return muestra

    def _poner_dibujo(self, clave):
        self.dibujo = clave
        self._refrescar_dibujos()

    def _refrescar_dibujos(self):
        for clave, b in self.botones_dibujo.items():
            b.setIcon(QIcon(iconos.miniatura(clave, self.color_icono)))
            b.setChecked(clave == self.dibujo)

    @staticmethod
    def _pintar_muestra(etq, hexa):
        c = QColor(hexa)
        texto = "#111827" if c.lightness() > 140 else "white"
        etq.setStyleSheet(f"background:{hexa};color:{texto};border-radius:6px;padding:3px;")

    def _elegir(self, cual):
        actual = QColor(self.color_fondo if cual == "fondo" else self.color_icono)
        c = QColorDialog.getColor(actual, self, "Elige un color")
        if c.isValid():
            self._poner_color(cual, c.name())

    def _poner_color(self, cual, hexa):
        if cual == "fondo":
            self.color_fondo = hexa
            self._pintar_muestra(self.muestra_fondo, hexa)
            claro = QColor(hexa).lightness() > 140
            self.estado.setText("Ese fondo es muy claro: el texto blanco no se leería bien. Elige uno más oscuro." if claro else "")
        else:
            self.color_icono = hexa
            self._pintar_muestra(self.muestra_icono, hexa)
            self._refrescar_dibujos()

    def _guardar(self):
        if QColor(self.color_fondo).lightness() > 140:
            self.estado.setText("Elige un fondo más oscuro para que el texto se lea.")
            return
        if self.c_inicio.isEnabled() and self.c_inicio.isChecked() != self.inicio_antes:
            try:
                (inicio_auto.activar if self.c_inicio.isChecked() else inicio_auto.desactivar)()
            except Exception as e:
                self.estado.setText(f"No pude cambiar el inicio automático ({type(e).__name__}).")
                return
        self.a["escala"] = ESCALAS[self.c_tam.currentText()]
        self.a["resumen_activo"] = self.c_resumen.isChecked()
        self.a["hora_resumen"] = self.hora.time().toString("HH:mm")
        self.a["color_fondo"] = self.color_fondo
        self.a["color_icono"] = self.color_icono
        self.a["dibujo_icono"] = self.dibujo
        self.a.guardar()
        self.accept()
