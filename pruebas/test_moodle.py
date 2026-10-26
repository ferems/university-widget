import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import ajustes, ical  # noqa: E402
from app.almacen import Almacen  # noqa: E402
from app.canvas_api import ErrorAutenticacion  # noqa: E402
from app.plataformas.moodle import ClienteMoodle  # noqa: E402
from app.servicio import Servicio  # noqa: E402

AHORA = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
T = lambda d, h=12: int(datetime(2026, 10, d, h, tzinfo=timezone.utc).timestamp())  # noqa: E731

RESPUESTAS = {
    "core_webservice_get_site_info": {"userid": 7, "fullname": "Estudiante"},
    "core_enrol_get_users_courses": [
        {"id": 1, "fullname": "Bases de Datos", "shortname": "BD", "startdate": T(1), "enddate": T(30) + 86400 * 60},
        {"id": 2, "fullname": "Curso viejo", "shortname": "OLD", "startdate": 1, "enddate": 100},
    ],
    "gradereport_overview_get_course_grades": {"grades": [{"courseid": 1, "grade": "88.50", "rawgrade": "88.5"}]},
    "core_calendar_get_action_events_by_timesort": {"events": [
        {"id": 10, "name": "Proyecto vence", "timesort": T(28), "modulename": "assign", "instance": 5,
         "course": {"fullname": "Bases de Datos"}, "url": "https://aula.edu.hn/mod/assign/view.php?id=9"},
        {"id": 11, "name": "Quiz 3", "timesort": T(27), "modulename": "quiz", "instance": 2,
         "course": {"fullname": "Bases de Datos"}, "url": "/mod/quiz/view.php?id=4"},
        {"id": 12, "name": "Ya entregada", "timesort": T(29), "modulename": "assign", "instance": 6,
         "course": {"fullname": "Bases de Datos"}, "url": "https://aula.edu.hn/x"},
    ]},
    "mod_forum_get_forums_by_courses": [{"id": 3, "course": 1, "type": "news"}, {"id": 4, "course": 1, "type": "general"}],
    "mod_forum_get_forum_discussions": {"discussions": [
        {"discussion": 55, "name": "Cambio de aula", "message": "<p>Ahora es en el <b>B2</b></p>", "timemodified": T(24)}]},
    "gradereport_user_get_grade_items": {"usergrades": [{"gradeitems": [
        {"id": 1, "itemtype": "mod", "itemname": "Parcial 1", "graderaw": 90, "grademax": 100, "gradedategraded": T(23)},
        {"id": 2, "itemtype": "mod", "itemname": "Sin nota", "graderaw": None, "grademax": 100, "gradedategraded": 0},
        {"id": 3, "itemtype": "course", "itemname": None, "graderaw": 88, "grademax": 100, "gradedategraded": T(23)}]}]},
}


class Resp:
    def __init__(self, js):
        self.js = js

    def raise_for_status(self):
        pass

    def json(self):
        return self.js


class SesionMoodle:
    def __init__(self, respuestas=None):
        self.r = dict(RESPUESTAS if respuestas is None else respuestas)
        self.llamadas = []

    def post(self, url, data=None, timeout=None):
        assert url.endswith("/webservice/rest/server.php") and "wstoken" not in url
        self.llamadas.append(data)
        f = data["wsfunction"]
        if f == "mod_assign_get_submission_status":
            enviada = data["assignid"] == 6
            return Resp({"lastattempt": {"submission": {"status": "submitted" if enviada else "new"}}})
        return Resp(self.r.get(f, self.r.get("*")))

    def get(self, *a, **k):
        raise AssertionError("Moodle no debe usar GET aqui")


def cliente(ses=None):
    return ClienteMoodle("TOKEN-DE-PRUEBA", "https://aula.edu.hn", ses or SesionMoodle())


def test_moodle_descarga_todo():
    pend, act, fuente, ex = cliente().descargar(AHORA, 3, 60)
    assert fuente == "api"
    por_titulo = {p.titulo: p for p in pend}
    assert por_titulo["Proyecto vence"].entregada is False
    assert por_titulo["Ya entregada"].entregada is True
    assert por_titulo["Quiz 3"].entregada is None and por_titulo["Quiz 3"].url == "https://aula.edu.hn/mod/quiz/view.php?id=4"
    assert [c.nombre for c in ex["cursos"]] == ["Bases de Datos"] and ex["cursos"][0].promedio == 88.5
    assert ex["anuncios"][0].texto == "Ahora es en el B2" and ex["anuncios"][0].materia == "Bases de Datos"
    assert ex["anuncios"][0].url.endswith("discuss.php?d=55")
    assert [(n.titulo, n.texto) for n in ex["notas"]] == [("Parcial 1", "90 / 100")]
    assert {a.tipo for a in act} == {"anuncio", "calificacion"}


def test_moodle_solo_funciones_de_lectura():
    ses = SesionMoodle()
    cliente(ses).descargar(AHORA, 3, 60)
    assert ses.llamadas and all(d["wsfunction"] in __import__("app.plataformas.moodle", fromlist=["x"]).FUNCIONES_LECTURA
                                for d in ses.llamadas)
    with pytest.raises(ValueError):
        cliente()._llamar("mod_assign_save_submission")


def test_moodle_token_malo():
    ses = SesionMoodle({"*": {"exception": "x", "errorcode": "invalidtoken"}})
    with pytest.raises(ErrorAutenticacion):
        cliente(ses).descargar(AHORA, 3, 60)


def test_moodle_secundarios_fallan_sin_tumbar():
    r = dict(RESPUESTAS)
    r["mod_forum_get_forums_by_courses"] = {"exception": "x", "errorcode": "algo"}
    pend, act, _, ex = cliente(SesionMoodle(r)).descargar(AHORA, 3, 60)
    assert pend and ex["anuncios"] == [] and ex["notas"]


class Cred:
    def __init__(self, valores):
        self.v = valores

    def obtener(self, k):
        return self.v.get(k)


def test_servicio_usa_moodle_y_avisa_solo_novedades(tmp_path):
    ses = SesionMoodle()
    s = Servicio(Almacen(tmp_path), Cred({"moodle_token": "t"}), leer_tareas=lambda: {},
                 moodle_fabrica=lambda t: ClienteMoodle(t, "https://aula.edu.hn", ses), plataforma=lambda: "moodle")
    r1 = s.refrescar(AHORA)
    assert not r1.sin_credenciales and r1.fuente == "api" and r1.avisos == []
    assert [p.titulo for p in r1.pendientes] == ["Quiz 3", "Proyecto vence"]  # la entregada no sale
    assert r1.cursos[0].promedio == 88.5 and r1.anuncios and r1.notas
    ses.r["mod_forum_get_forum_discussions"] = {"discussions": [
        {"discussion": 56, "name": "Nuevo aviso", "message": "hola", "timemodified": T(25)}]}
    r2 = s.refrescar(AHORA)
    assert len(r2.avisos) == 1 and "Nuevo aviso" in r2.avisos[0].mensaje


def test_servicio_respeta_plataforma_ical_aunque_haya_token(tmp_path):
    s = Servicio(Almacen(tmp_path), Cred({"token": "t", "ical_url": "https://x/c.ics"}), leer_tareas=lambda: {},
                 lector_ical=lambda u: ical.parsear(ICS, AHORA), plataforma=lambda: "ical")
    r = s.refrescar(AHORA)
    assert r.fuente == "ical" and [p.titulo for p in r.pendientes] == ["Clase"]


ICS = """BEGIN:VEVENT
UID:c1
SUMMARY:Clase
DTSTART;TZID=America/Tegucigalpa:20261026T180000
RRULE:FREQ=WEEKLY;COUNT=3
END:VEVENT
"""


def test_ical_repeticiones():
    r = ical.parsear(ICS, AHORA)
    assert len(r) == 3 and len({p.id for p in r}) == 3
    assert [p.vence.day for p in r] == [26, 2, 9]


def test_ical_repeticion_excluida_y_movida():
    t = ICS.replace("COUNT=3", "COUNT=3\nEXDATE;TZID=America/Tegucigalpa:20261102T180000") + \
        "BEGIN:VEVENT\nUID:c1\nSUMMARY:Clase\nRECURRENCE-ID;TZID=America/Tegucigalpa:20261109T180000\n" \
        "DTSTART;TZID=America/Tegucigalpa:20261110T100000\nEND:VEVENT\n"
    r = ical.parsear(t, AHORA)
    assert sorted(p.vence.day for p in r) == [10, 26]


def test_ical_diario_hasta_fecha():
    t = "BEGIN:VEVENT\nUID:d\nSUMMARY:Repaso\nDTSTART:20261026T150000Z\nRRULE:FREQ=DAILY;UNTIL=20261028T235959Z\nEND:VEVENT\n"
    assert [p.vence.day for p in ical.parsear(t, AHORA)] == [26, 27, 28]


def test_url_moodle_con_carpeta():
    assert ajustes.normalizar_url("campus.uni.edu.hn/moodle/", True, "Moodle") == "https://campus.uni.edu.hn/moodle"
    assert ajustes.normalizar_url("https://campus.uni.edu.hn/moodle/my/?x=1", True) == "https://campus.uni.edu.hn/moodle/my"
    assert ajustes.normalizar_url("https://campus.uni.edu.hn/moodle", False) == "https://campus.uni.edu.hn"
    with pytest.raises(ValueError):
        ajustes.normalizar_url("https://campus.uni.edu.hn/a b/<x>", True)
    with pytest.raises(ValueError):
        ajustes.normalizar_url("http://campus.uni.edu.hn", True)
