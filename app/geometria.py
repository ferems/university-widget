"""Posicion del widget: hacia donde se expande y como se pega a los bordes. Rectangulos = (x, y, ancho, alto)."""
from __future__ import annotations

from typing import Tuple

Rect = Tuple[int, int, int, int]


def expandir(icono: Rect, panel: Tuple[int, int], pantalla: Rect) -> Tuple[Rect, str]:
    """Devuelve el rectangulo del panel y la esquina donde queda el icono ('tl','tr','bl','br').
    Si el icono esta en la mitad de abajo, el panel crece hacia arriba; si esta a la derecha, hacia la izquierda."""
    x, y, w, h = icono
    px_, py_, pw_, ph_ = pantalla
    pw, ph = min(panel[0], pw_), min(panel[1], ph_)
    abajo = (y + h / 2) > (py_ + ph_ / 2)
    derecha = (x + w / 2) > (px_ + pw_ / 2)
    nx = x + w - pw if derecha else x
    ny = y + h - ph if abajo else y
    nx = max(px_, min(nx, px_ + pw_ - pw))
    ny = max(py_, min(ny, py_ + ph_ - ph))
    return (nx, ny, pw, ph), ("b" if abajo else "t") + ("r" if derecha else "l")


def contraer(panel: Rect, ancla: str, icono: Tuple[int, int]) -> Tuple[int, int]:
    """Posicion (x, y) del icono dentro del panel, en la esquina que lo tenia."""
    x, y, w, h = panel
    iw, ih = icono
    return (x + w - iw if ancla[1] == "r" else x), (y + h - ih if ancla[0] == "b" else y)


def pegar_a_borde(pos: Tuple[int, int], tam: Tuple[int, int], pantalla: Rect, umbral: int = 28, margen: int = 4) -> Tuple[int, int]:
    x, y = pos
    w, h = tam
    px_, py_, pw_, ph_ = pantalla
    if abs(x - px_) <= umbral:
        x = px_ + margen
    elif abs((x + w) - (px_ + pw_)) <= umbral:
        x = px_ + pw_ - w - margen
    if abs(y - py_) <= umbral:
        y = py_ + margen
    elif abs((y + h) - (py_ + ph_)) <= umbral:
        y = py_ + ph_ - h - margen
    return x, y


def dentro(pos: Tuple[int, int], tam: Tuple[int, int], pantalla: Rect) -> Tuple[int, int]:
    px_, py_, pw_, ph_ = pantalla
    return (max(px_, min(pos[0], px_ + pw_ - tam[0])), max(py_, min(pos[1], py_ + ph_ - tam[1])))
