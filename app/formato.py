"""Textos de fechas y cuentas regresivas en espanol."""
from __future__ import annotations

from datetime import datetime, timedelta

from .config import ZONA

DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def fecha_hora(dt: datetime) -> str:
    local = dt.astimezone(ZONA)
    hora = local.hour % 12 or 12
    sufijo = "AM" if local.hour < 12 else "PM"
    return f"{DIAS[local.weekday()]} {local.day} {MESES[local.month - 1]}, {hora}:{local.minute:02d} {sufijo}"


def _corto(segundos: int, con_segundos: bool) -> str:
    d, resto = divmod(segundos, 86400)
    h, resto = divmod(resto, 3600)
    m, s = divmod(resto, 60)
    if d:
        return f"{d} d" + (f" {h} h" if h else "")
    if h:
        return f"{h} h" + (f" {m} min" if m else "")
    if m:
        return f"{m} min {s} s" if con_segundos else f"{m} min"
    return f"{s} s" if con_segundos else "menos de 1 min"


def cuenta(delta: timedelta, con_segundos: bool = False) -> str:
    seg = int(delta.total_seconds())
    if seg < 0:
        return "vencida hace " + _corto(-seg, False)
    return "en " + _corto(seg, con_segundos)
