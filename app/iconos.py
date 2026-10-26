"""Dibujos para el ícono redondo (todo dibujado con codigo, sin imagenes)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

DIBUJOS = [("check", "Palomita"), ("libro", "Libro"), ("birrete", "Birrete de graduación"),
           ("lapiz", "Lápiz"), ("campana", "Campana"), ("reloj", "Reloj")]


def _pts(x, y, d, puntos):
    return QPolygonF([QPointF(x + d * a, y + d * b) for a, b in puntos])


def dibujar(p: QPainter, clave: str, x: float, y: float, d: float, fondo: QColor) -> None:
    """Dibuja el simbolo en blanco dentro del circulo (x, y, d, d). `fondo` se usa para los huecos."""
    p.save()
    blanco = QColor("white")
    p.setRenderHint(QPainter.Antialiasing)
    trazo = QPen(blanco, d * 0.07, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    relleno = lambda: (p.setPen(Qt.NoPen), p.setBrush(blanco))  # noqa: E731
    if clave == "libro":
        relleno()
        p.drawPolygon(_pts(x, y, d, [(.20, .33), (.47, .39), (.47, .72), (.20, .66)]))
        p.drawPolygon(_pts(x, y, d, [(.80, .33), (.53, .39), (.53, .72), (.80, .66)]))
        p.setPen(QPen(fondo, d * 0.025, Qt.SolidLine, Qt.RoundCap))
        for yy in (.48, .56, .64):  # renglones
            p.drawLine(QPointF(x + d * .26, y + d * (yy - .03)), QPointF(x + d * .41, y + d * (yy + .0)))
            p.drawLine(QPointF(x + d * .74, y + d * (yy - .03)), QPointF(x + d * .59, y + d * (yy + .0)))
    elif clave == "birrete":
        relleno()
        p.drawPolygon(_pts(x, y, d, [(.50, .26), (.86, .43), (.50, .60), (.14, .43)]))
        p.drawPolygon(_pts(x, y, d, [(.28, .54), (.50, .64), (.72, .54), (.72, .68), (.50, .78), (.28, .68)]))
        p.setPen(QPen(blanco, d * 0.035, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(x + d * .84, y + d * .45), QPointF(x + d * .84, y + d * .66))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(x + d * .84, y + d * .69), d * .04, d * .04)
    elif clave == "lapiz":
        p.translate(x + d / 2, y + d / 2)
        p.rotate(-45)
        relleno()
        p.drawRoundedRect(QRectF(-d * .30, -d * .075, d * .42, d * .15), d * .02, d * .02)
        p.drawPolygon(QPolygonF([QPointF(d * .14, -d * .075), QPointF(d * .32, 0), QPointF(d * .14, d * .075)]))
        p.setPen(QPen(fondo, d * 0.025))
        p.drawLine(QPointF(-d * .20, -d * .075), QPointF(-d * .20, d * .075))
    elif clave == "campana":
        relleno()
        c = QPainterPath()
        c.moveTo(x + d * .26, y + d * .64)
        c.cubicTo(x + d * .34, y + d * .57, x + d * .33, y + d * .48, x + d * .37, y + d * .41)
        c.cubicTo(x + d * .41, y + d * .31, x + d * .59, y + d * .31, x + d * .63, y + d * .41)
        c.cubicTo(x + d * .67, y + d * .48, x + d * .66, y + d * .57, x + d * .74, y + d * .64)
        c.closeSubpath()
        p.drawPath(c)
        p.drawEllipse(QPointF(x + d * .50, y + d * .72), d * .055, d * .05)
        p.drawEllipse(QPointF(x + d * .50, y + d * .30), d * .035, d * .035)
    elif clave == "reloj":
        p.setPen(trazo)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(x + d / 2, y + d / 2), d * .25, d * .25)
        p.drawLine(QPointF(x + d / 2, y + d / 2), QPointF(x + d / 2, y + d * .35))
        p.drawLine(QPointF(x + d / 2, y + d / 2), QPointF(x + d * .62, y + d * .56))
    else:  # palomita
        p.setPen(QPen(blanco, d * 0.09, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline(_pts(x, y, d, [(.29, .52), (.44, .67), (.72, .35)]))
    p.restore()


def miniatura(clave: str, color: str, lado: int = 44) -> QPixmap:
    pm = QPixmap(lado, lado)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(1, 1, lado - 2, lado - 2)
    dibujar(p, clave, 1, 1, lado - 2, QColor(color))
    p.end()
    return pm
