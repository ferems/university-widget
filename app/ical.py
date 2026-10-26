"""Lee un calendario iCal (.ics). Sirve para la 'Fuente de calendario' de Canvas y para cualquier otra
plataforma que permita exportar o suscribirse a su calendario (Moodle, Google Classroom/Calendar, etc.)."""
from __future__ import annotations

import re
from datetime import date, datetime, time, timezone
from typing import List
from zoneinfo import ZoneInfo

import requests

from .ajustes import url_canvas
from .config import ZONA
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

    # Canvas marca sus tareas con "assignment" en el UID; en otras plataformas se toman todos los eventos con fecha.
    es_canvas = any("assignment" in ev.get("UID", ("", []))[0] for ev in eventos)
    salida: List[Pendiente] = []
    for ev in eventos:
        uid = ev.get("UID", ("", []))[0]
        if es_canvas and "assignment" not in uid:  # solo tareas/quices, no eventos de calendario
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
        elif "CATEGORIES" in ev:  # Moodle y otros guardan aqui el nombre del curso
            materia = _desescapar(ev["CATEGORIES"][0]).split(",")[0].strip()
        url = _desescapar(ev["URL"][0]) if "URL" in ev else (url_canvas() if es_canvas else "")
        ident = uid or f"{resumen}|{ev['DTSTART'][0]}"
        salida.append(Pendiente(id=ident, titulo=resumen or "(sin nombre)", materia=materia,
                                vence=vence, url=url, entregada=None))
    return salida


def leer(enlace: str) -> List[Pendiente]:
    enlace = enlace.strip()
    if enlace.startswith("webcal://"):
        enlace = "https://" + enlace[len("webcal://"):]
    r = requests.get(enlace, timeout=20)
    r.raise_for_status()
    return parsear(r.text)
