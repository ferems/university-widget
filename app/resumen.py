"""Calculos del resumen de hoy / de la semana (sin ventanas)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Callable, Dict, List, Tuple

from .config import ZONA
from .modelos import Pendiente


def limites_semana(ahora: datetime) -> Tuple[date, date]:
    """Lunes y domingo de la semana actual (hora de Honduras)."""
    hoy = ahora.astimezone(ZONA).date()
    lunes = hoy - timedelta(days=hoy.weekday())
    return lunes, lunes + timedelta(days=6)


def en_semana(dt: datetime, ahora: datetime) -> bool:
    a, b = limites_semana(ahora)
    return a <= dt.astimezone(ZONA).date() <= b


def estadisticas(pendientes: List[Pendiente], hecha: Callable[[str], bool], entregadas_semana: int, ahora: datetime) -> Dict:
    hoy = ahora.astimezone(ZONA).date()
    activos = [p for p in pendientes if not hecha(p.id)]
    vencen_hoy = [p for p in activos if p.vence >= ahora and p.vence.astimezone(ZONA).date() == hoy]
    vencidas = [p for p in activos if p.vence < ahora]
    de_semana = [p for p in pendientes if en_semana(p.vence, ahora)]
    hechas_locales = sum(1 for p in de_semana if hecha(p.id))
    total = len(de_semana) + entregadas_semana
    hechas = hechas_locales + entregadas_semana
    return {"hoy": vencen_hoy, "vencidas": vencidas, "activos": activos,
            "semana_total": total, "semana_hechas": hechas, "semana_faltan": total - hechas}


def texto_resumen(est: Dict) -> Tuple[str, str]:
    hoy = est["hoy"]
    if hoy:
        nombres = ", ".join(p.titulo for p in hoy[:3]) + ("…" if len(hoy) > 3 else "")
        linea1 = f"Hoy vence{'n' if len(hoy) != 1 else ''} {len(hoy)}: {nombres}."
    else:
        linea1 = "Hoy no vence nada."
    faltan, total = est["semana_faltan"], est["semana_total"]
    linea2 = f"Esta semana te faltan {faltan} de {total}." if total else "Esta semana no tienes entregas."
    extra = f" Tienes {len(est['vencidas'])} vencida(s)." if est["vencidas"] else ""
    return "Resumen de tu semana", f"{linea1} {linea2}{extra}"
