"""Lee un calendario iCal (.ics). Sirve para la 'Fuente de calendario' de Canvas y para cualquier otra
plataforma que permita exportar o suscribirse a su calendario (Moodle, Google Classroom/Calendar, etc.)."""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
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


_DIAS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def repeticiones(inicio: datetime, regla: str, excluidas: set, desde: datetime, hasta: datetime) -> List[datetime]:
    """Fechas de un evento que se repite (RRULE) dentro de [desde, hasta]. Soporta DAILY, WEEKLY (con BYDAY),
    MONTHLY y YEARLY, con INTERVAL, COUNT y UNTIL. Mantiene la hora local del evento."""
    r = dict(x.split("=", 1) for x in regla.split(";") if "=" in x)
    freq, paso = r.get("FREQ", ""), max(int(r.get("INTERVAL", "1") or 1), 1)
    cuenta = int(r["COUNT"]) if r.get("COUNT", "").isdigit() else None
    fin = _fecha(r["UNTIL"], []) if r.get("UNTIL") else None
    local = inicio.replace(tzinfo=None)
    zona = inicio.tzinfo
    dias = [_DIAS[d[-2:]] for d in r.get("BYDAY", "").split(",") if d[-2:] in _DIAS] or [inicio.weekday()]
    candidatos: List[datetime] = []
    if freq == "DAILY":
        n = 0
        while n < 4000:
            candidatos.append(local + timedelta(days=paso * n))
            n += 1
    elif freq == "WEEKLY":
        lunes = local - timedelta(days=local.weekday())
        for n in range(0, 800):
            for d in sorted(dias):
                c = lunes + timedelta(weeks=paso * n, days=d)
                if c >= local:
                    candidatos.append(c)
    elif freq in ("MONTHLY", "YEARLY"):
        meses = paso if freq == "MONTHLY" else 12 * paso
        for n in range(0, 600):
            total = local.month - 1 + meses * n
            try:
                candidatos.append(local.replace(year=local.year + total // 12, month=total % 12 + 1))
            except ValueError:
                continue  # por ejemplo 31 de un mes de 30 dias
    else:
        return []
    salida = []
    for i, c in enumerate(candidatos):
        if cuenta is not None and i >= cuenta:
            break
        f = c.replace(tzinfo=zona)
        if fin is not None and f > fin:
            break
        if f > hasta:
            break
        if f >= desde and f not in excluidas:
            salida.append(f)
    return salida


def parsear(texto: str, ahora: datetime | None = None) -> List[Pendiente]:
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
            if campo.upper() == "EXDATE":
                actual.setdefault("EXDATES", []).extend((v, params) for v in valor.split(","))
            else:
                actual[campo.upper()] = (valor, params)

    # Canvas marca sus tareas con "assignment" en el UID; en otras plataformas se toman todos los eventos con fecha.
    es_canvas = any("assignment" in ev.get("UID", ("", []))[0] for ev in eventos)
    ahora = ahora or datetime.now(timezone.utc)
    ventana = (ahora - timedelta(days=5), ahora + timedelta(days=75))
    cambiados = {(ev["UID"][0], _fecha(*ev["RECURRENCE-ID"])) for ev in eventos if "UID" in ev and "RECURRENCE-ID" in ev}
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
        if "RRULE" in ev:  # evento que se repite: una tarea por cada fecha dentro de la ventana
            excluidas = {f for f in (_fecha(*x) for x in ev.get("EXDATES", [])) if f}
            excluidas |= {f for (u, f) in cambiados if u == uid and f}
            for f in repeticiones(vence, ev["RRULE"][0], excluidas, *ventana):
                salida.append(Pendiente(id=f"{ident}|{f.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%S')}",
                                        titulo=resumen or "(sin nombre)", materia=materia, vence=f, url=url, entregada=None))
            continue
        if "RECURRENCE-ID" in ev and (f := _fecha(*ev["RECURRENCE-ID"])):  # una repeticion movida: mismo id que la original
            ident = f"{ident}|{f.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
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
