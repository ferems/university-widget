import json
import sys
from datetime import timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import ajustes, ical  # noqa: E402
from app.canvas_api import ClienteCanvas  # noqa: E402
from app.config import URL_CANVAS  # noqa: E402
from test_logica import SesionFalsa  # noqa: E402

MOODLE = """BEGIN:VCALENDAR
PRODID:-//Moodle Pty Ltd//NONSGML Moodle Version 2024//EN
BEGIN:VEVENT
UID:4821@aula.universidad.edu
SUMMARY:Entrega del proyecto final
CATEGORIES:Bases de Datos II
DTSTART:20261101T235900Z
DTEND:20261101T235900Z
URL:https://aula.universidad.edu/mod/assign/view.php?id=77
END:VEVENT
BEGIN:VEVENT
SUMMARY:Foro de la semana 5
DTSTART;TZID=America/Tegucigalpa:20261103T180000
END:VEVENT
BEGIN:VEVENT
UID:evento-sin-fecha
SUMMARY:No tiene fecha
END:VEVENT
END:VCALENDAR
"""


def test_ical_de_otra_plataforma_toma_todos_los_eventos_con_fecha():
    r = ical.parsear(MOODLE)
    assert len(r) == 2
    assert (r[0].titulo, r[0].materia) == ("Entrega del proyecto final", "Bases de Datos II")
    assert r[0].url == "https://aula.universidad.edu/mod/assign/view.php?id=77"
    # sin UID se inventa uno estable; sin URL queda vacio; la hora de Tegucigalpa se respeta (18:00 = 00:00 UTC)
    assert r[1].id.startswith("Foro de la semana 5|") and r[1].url == ""
    en_utc = r[1].vence.astimezone(timezone.utc)
    assert (en_utc.day, en_utc.hour) == (4, 0)


def test_en_un_feed_de_canvas_solo_se_toman_las_tareas():
    canvas = ("BEGIN:VEVENT\nUID:event-assignment-1\nDTSTART:20261101T235900Z\nSUMMARY:Tarea [Redes]\nEND:VEVENT\n"
              "BEGIN:VEVENT\nUID:event-calendar-event-9\nDTSTART:20261101T150000Z\nSUMMARY:Clase\nEND:VEVENT\n")
    assert [p.titulo for p in ical.parsear(canvas)] == ["Tarea"]


@pytest.mark.parametrize("texto, esperado", [
    ("https://uni.instructure.com", "https://uni.instructure.com"),
    ("uni.instructure.com", "https://uni.instructure.com"),
    ("  https://uni.instructure.com/courses/12?x=1  ", "https://uni.instructure.com"),
    ("https://canvas.mi-uni.edu.hn:8443/", "https://canvas.mi-uni.edu.hn:8443"),
])
def test_normalizar_url_valida(texto, esperado):
    assert ajustes.normalizar_url(texto) == esperado


@pytest.mark.parametrize("texto", ["", "   ", "http://uni.instructure.com", "ftp://uni.com", "https://localhost",
                                   "https://uni .com", "https://a_b.com", "javascript:alert(1)"])
def test_normalizar_url_rechaza_lo_inseguro_o_raro(texto):
    with pytest.raises(ValueError):
        ajustes.normalizar_url(texto)


def test_url_canvas_usa_la_configurada_o_la_de_config(tmp_path):
    assert ajustes.url_canvas(tmp_path) == URL_CANVAS
    (tmp_path / "ajustes.json").write_text(json.dumps({"url_canvas": "otra.instructure.com"}), encoding="utf-8")
    assert ajustes.url_canvas(tmp_path) == "https://otra.instructure.com"
    (tmp_path / "ajustes.json").write_text(json.dumps({"url_canvas": "http://malo.com"}), encoding="utf-8")
    assert ajustes.url_canvas(tmp_path) == URL_CANVAS  # un valor invalido nunca recibe el token


def test_cliente_usa_la_direccion_indicada():
    assert ClienteCanvas("T", base="https://otra.instructure.com/", sesion=SesionFalsa({})).base == "https://otra.instructure.com"
