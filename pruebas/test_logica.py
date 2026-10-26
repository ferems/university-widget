import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import formato, ical, recordatorios  # noqa: E402
from app.almacen import Almacen  # noqa: E402
from app.canvas_api import ClienteCanvas, ErrorAutenticacion  # noqa: E402
from app.modelos import Pendiente  # noqa: E402
from app.servicio import Servicio  # noqa: E402

AHORA = datetime(2026, 10, 25, 18, 0, tzinfo=timezone.utc)


def pend(id_, horas, entregada=False):
    return Pendiente(id_, f"Tarea {id_}", "Materia", AHORA + timedelta(hours=horas), "https://x/y", entregada)


# ---------- recordatorios ----------
def test_recordatorios_sin_duplicados():
    n = {}
    p = [pend("a", 23)]
    assert [r.nivel for r in recordatorios.calcular(p, AHORA, n)] == ["24h"]
    assert recordatorios.calcular(p, AHORA, n) == []
    assert [r.nivel for r in recordatorios.calcular(p, AHORA + timedelta(hours=21), n)] == ["3h"]
    assert [r.nivel for r in recordatorios.calcular(p, AHORA + timedelta(hours=22.5), n)] == ["1h"]
    assert recordatorios.calcular(p, AHORA + timedelta(hours=22.6), n) == []
    assert [r.nivel for r in recordatorios.calcular(p, AHORA + timedelta(hours=24), n)] == ["vencida"]
    assert recordatorios.calcular(p, AHORA + timedelta(hours=30), n) == []


def test_app_abierta_tarde_solo_manda_el_mas_urgente():
    n = {}
    r = recordatorios.calcular([pend("a", 0.5)], AHORA, n)
    assert [x.nivel for x in r] == ["1h"]


def test_lejanas_y_entregadas_no_avisan():
    assert recordatorios.calcular([pend("a", 30), pend("b", 0.5, entregada=True)], AHORA, {}) == []


def test_vencida_desconocida_no_avisa():
    assert recordatorios.calcular([pend("a", -1, entregada=None)], AHORA, {}) == []


def test_si_cambia_la_fecha_vuelve_a_avisar():
    n = {}
    assert recordatorios.calcular([pend("a", 2)], AHORA, n)
    assert recordatorios.calcular([pend("a", 2.5)], AHORA, n)  # otra fecha de entrega


# ---------- formato ----------
def test_formato():
    assert formato.fecha_hora(datetime(2026, 10, 31, 5, 59, tzinfo=timezone.utc)) == "vie 30 oct, 11:59 PM"
    assert formato.cuenta(timedelta(hours=2, minutes=15)) == "en 2 h 15 min"
    assert formato.cuenta(timedelta(days=2, hours=3)) == "en 2 d 3 h"
    assert formato.cuenta(timedelta(minutes=42, seconds=10), True) == "en 42 min 10 s"
    assert formato.cuenta(timedelta(hours=-3)) == "vencida hace 3 h"


# ---------- iCal ----------
ICS = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event-assignment-111
DTSTART:20261030T235900Z
SUMMARY:Tarea 3\\, entrega [Ingeniería de Software]
URL:https://unitechonduras.instructure.com/courses/1/assignments/111
END:VEVENT
BEGIN:VEVENT
UID:event-calendar-event-5
DTSTART:20261030T150000Z
SUMMARY:Clase en vivo [Ingeniería]
END:VEVENT
BEGIN:VEVENT
UID:event-assignment-222
DTSTART;VALUE=DATE:20261101
SUMMARY:Proyecto largo
 con salto de línea [Redes]
END:VEVENT
END:VCALENDAR
"""


def test_ical():
    r = ical.parsear(ICS)
    assert len(r) == 2
    assert (r[0].titulo, r[0].materia) == ("Tarea 3, entrega", "Ingeniería de Software")
    assert r[0].url.endswith("/assignments/111") and r[0].entregada is None
    assert r[1].materia == "Redes" and r[1].titulo.startswith("Proyecto largo")
    assert formato.fecha_hora(r[1].vence).endswith("11:59 PM")


# ---------- API con respuestas simuladas ----------
class Resp:
    def __init__(self, datos, status=200, links=None):
        self.datos, self.status_code, self.links = datos, status, links or {}

    def json(self):
        return self.datos

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


class SesionFalsa:
    def __init__(self, rutas):
        self.rutas, self.headers, self.llamadas = dict(rutas), {}, []

    def get(self, url, params=None, timeout=None):
        self.llamadas.append(("GET", url))
        for ruta, resp in self.rutas.items():
            if url.endswith(ruta):
                if isinstance(resp, Exception):
                    raise resp
                return resp
        return Resp([], 404)


PLANNER = [
    {"plannable_type": "assignment", "plannable_id": 1, "context_name": "Redes", "html_url": "/courses/9/assignments/1",
     "plannable": {"id": 1, "title": "Laboratorio 2", "due_at": "2026-10-26T05:59:00Z"},
     "submissions": {"submitted": False}},
    {"plannable_type": "assignment", "plannable_id": 2, "context_name": "Redes", "html_url": "/courses/9/assignments/2",
     "plannable": {"id": 2, "title": "Ya entregada", "due_at": "2026-10-27T05:59:00Z"},
     "submissions": {"submitted": True}},
    {"plannable_type": "planner_note", "plannable": {"title": "nota", "todo_date": "2026-10-26T00:00:00Z"}},
]
ACTIVIDAD = [
    {"id": 7, "type": "Announcement", "title": "Cambio de aula", "message": "<p>Ahora en <b>B-2</b></p>", "course_id": 9, "html_url": "https://x/a"},
    {"id": 8, "type": "Submission", "title": "Laboratorio 1", "grade": "95", "course_id": 9, "html_url": "https://x/s"},
]


def servicio(tmp_path, rutas, token="T", enlace=None):
    class Cred:
        def obtener(self, n):
            return {"token": token, "ical_url": enlace}.get(n)

    ses = SesionFalsa(rutas)
    return Servicio(Almacen(tmp_path), Cred(), lambda t: ClienteCanvas(t, sesion=ses)), ses


RUTAS = {"/planner/items": Resp(PLANNER), "/users/self/courses": Resp([{"id": 9, "name": "Redes"}]),
         "/activity_stream": Resp(ACTIVIDAD)}


def test_api_primera_vez_no_avisa_y_solo_lee(tmp_path):
    s, ses = servicio(tmp_path, RUTAS)
    r = s.refrescar(AHORA)
    assert [p.titulo for p in r.pendientes] == ["Laboratorio 2"]
    assert r.avisos == [] and r.fuente == "api"
    assert {m for m, _ in ses.llamadas} == {"GET"}
    assert [x.nivel for x in r.recordatorios] == ["24h"]
    # segunda vez: sin recordatorios repetidos
    assert s.refrescar(AHORA).recordatorios == []


def test_api_novedades_despues_de_la_primera(tmp_path):
    s, ses = servicio(tmp_path, RUTAS)
    s.refrescar(AHORA)
    ses.rutas["/planner/items"] = Resp(PLANNER + [{
        "plannable_type": "assignment", "plannable_id": 3, "context_name": "Redes", "html_url": "/c/3",
        "plannable": {"id": 3, "title": "Tarea nueva", "due_at": "2026-10-29T05:59:00Z"}, "submissions": {"submitted": False}}])
    ses.rutas["/activity_stream"] = Resp(ACTIVIDAD + [{"id": 9, "type": "Announcement", "title": "Otro anuncio", "course_id": 9}])
    r = s.refrescar(AHORA)
    assert sorted(a.tipo for a in r.avisos) == ["anuncio", "tarea"]
    assert s.refrescar(AHORA).avisos == []


def test_sin_internet_usa_datos_guardados(tmp_path):
    s, ses = servicio(tmp_path, RUTAS)
    s.refrescar(AHORA)
    ses.rutas["/planner/items"] = requests.ConnectionError("sin red")
    r = s.refrescar(AHORA)
    assert r.sin_conexion and [p.titulo for p in r.pendientes] == ["Laboratorio 2"]


def test_token_malo_sin_ical_da_mensaje(tmp_path):
    s, _ = servicio(tmp_path, {"/planner/items": Resp([], 401)})
    r = s.refrescar(AHORA)
    assert r.error and "token" in r.error


def test_token_malo_cae_a_ical(tmp_path):
    s, _ = servicio(tmp_path, {"/planner/items": Resp([], 401)}, enlace="https://ical")
    s.lector_ical = lambda url: ical.parsear(ICS)
    r = s.refrescar(datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc))
    assert r.fuente == "ical" and len(r.pendientes) == 2


def test_sin_credenciales(tmp_path):
    s, _ = servicio(tmp_path, RUTAS, token=None)
    assert s.refrescar(AHORA).sin_credenciales
