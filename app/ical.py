"""Alternativa sin token: lee la 'Fuente de calendario' (iCal) de Canvas."""
from __future__ import annotations

import re
from datetime import date, datetime, time, timezone
from typing import List
from zoneinfo import ZoneInfo

import requests

from .config import URL_CANVAS, ZONA
from .modelos import Pendiente


def _desescapar(t: str) -> str:
    return t.replace("\\n", " ").replace("\\N", " ").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def _fecha(valor: str, params: List[str]) -> datetime | None:
    valor = valor.strip()
    try:
        if "T" not in valor:  # evento de todo el dia
            d = date(int(valor[0:4]), int(valor[4:6]), int(valor[6:8]))
            return datetime.combine(d, time(23, 59), tzinfo=ZONA)
        base = datetime.strptime(valor.rstrip("Z"), "%Y%m%dT%H%M%S")
        if valor.endswith("Z"):
            return base.replace(tzinfo=timezone.utc)
        zona = ZONA
        for p in params:
            if p.upper().startswith("TZID="):
                try:
                    zona = ZoneInfo(p[5:])
                except Exception:
                    pass
        return base.replace(tzinfo=zona)
    except (ValueError, IndexError):
        return None


def parsear(texto: str) -> List[Pendiente]:
    lineas: List[str] = []
    for l in texto.splitlines():
        if l[:1] in (" ", "\t") and lineas:
            lineas[-1] += l[1:]
        else:
            lineas.append(l)

    eventos, actual = [], None
    for l in lineas:
        if l == "BEGIN:VEVENT":
            actual = {}
        elif l == "END:VEVENT":
            if actual is not None:
                eventos.append(actual)
            actual = None
        elif actual is not None and ":" in l:
            nombre, valor = l.split(":", 1)
            campo, *params = nombre.split(";")
            actual[campo.upper()] = (valor, params)

    salida: List[Pendiente] = []
    for ev in eventos:
        uid = ev.get("UID", ("", []))[0]
        if "assignment" not in uid:  # solo tareas/quices, no eventos de calendario
            continue
        if "DTSTART" not in ev or "SUMMARY" not in ev:
            continue
        vence = _fecha(*ev["DTSTART"])
        if vence is None:
            continue
        resumen = _desescapar(ev["SUMMARY"][0]).strip()
        materia = ""
        m = re.search(r"\[([^\]]+)\]\s*$", resumen)
        if m:
            materia = m.group(1)
            resumen = resumen[: m.start()].strip()
        url = _desescapar(ev["URL"][0]) if "URL" in ev else URL_CANVAS
        salida.append(Pendiente(id=uid, titulo=resumen or "(sin nombre)", materia=materia,
                                vence=vence, url=url, entregada=None))
    return salida


def leer(enlace: str) -> List[Pendiente]:
    enlace = enlace.strip()
    if enlace.startswith("webcal://"):
        enlace = "https://" + enlace[len("webcal://"):]
    r = requests.get(enlace, timeout=20)
    r.raise_for_status()
    return parsear(r.text)
