import logging
import logging.handlers
import sys

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap, QFont
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .config import DATOS, FUENTE
from .notificaciones import Notificador
from .servicio import Servicio
from .widget import WidgetCanvas


def crear_icono() -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#2563eb"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(4, 4, 56, 56)
    p.setPen(QColor("white"))
    p.setFont(QFont(FUENTE, 28, QFont.Bold))
    p.drawText(pm.rect(), Qt.AlignCenter, "C")
    p.end()
    return QIcon(pm)


def main() -> int:
    DATOS.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.handlers.RotatingFileHandler(DATOS / "registro.log", maxBytes=200_000, backupCount=1, encoding="utf-8")],
    )
    def _error_no_controlado(tipo, valor, tb):
        logging.getLogger("app").error("Error no controlado", exc_info=(tipo, valor, tb))

    sys.excepthook = _error_no_controlado
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("College Widget")

    bandeja = QSystemTrayIcon(crear_icono(), app)
    bandeja.setToolTip("College Widget")
    notificador = Notificador(bandeja)
    widget = WidgetCanvas(Servicio(), notificador, app)

    menu = QMenu()
    for texto, fn in (("Mostrar / ocultar widget", lambda: widget.setVisible(not widget.isVisible())),
                      ("Actualizar ahora", widget.actualizar_ahora),
                      ("Resumen de la semana ahora", widget.enviar_resumen),
                      ("Probar notificación", widget.probar_notificacion),
                      ("Ajustes…", widget.abrir_ajustes),
                      ("Conexión…", widget.abrir_conexion),
                      ("Salir", app.quit)):
        accion = QAction(texto, menu)
        accion.triggered.connect(fn)
        menu.addAction(accion)
    bandeja.setContextMenu(menu)
    bandeja.activated.connect(lambda motivo: widget.setVisible(not widget.isVisible()) if motivo == QSystemTrayIcon.Trigger else None)
    bandeja.show()

    widget.show()
    widget.raise_()
    g = widget.geometry()
    logging.info("Widget en x=%s y=%s (%sx%s), pantalla disponible=%s, devicePixelRatio=%s", g.x(), g.y(), g.width(),
                 g.height(), widget.screen().availableGeometry().getRect(), widget.devicePixelRatio())
    QTimer.singleShot(800, widget.actualizar_ahora)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
