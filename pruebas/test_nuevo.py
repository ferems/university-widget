import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import geometria, inicio_windows, recordatorios, resumen  # noqa: E402
from app.ajustes import Ajustes  # noqa: E402
from app.almacen import Almacen  # noqa: E402
from app.canvas_api import ClienteCanvas  # noqa: E402
from app.modelos import Pendiente  # noqa: E402
from app.servicio import Servicio  # noqa: E402
from app.tareas import EstadoTareas  # noqa: E402
from test_logica import ACTIVIDAD, PLANNER, Resp, SesionFalsa  # noqa: E402

UTC = timezone.utc
# domingo 25 oct 2026, 12:00 en Honduras
AHORA = datetime(2026, 10, 25, 18, 0, tzinfo=UTC)


def pend(id_, horas, entregada=False, materia="Redes"):
    return Pendiente(id_, f"Tarea {id_}", materia, AHORA + timedelta(hours=horas), "https://x/" + id_, entregada)


# ---------- cursos / periodo / promedio ----------
CURSOS = [
    {"id": 1, "name": "Redes", "course_code": "RED-1", "term": {"name": "Q4 2026", "start_at": "2026-10-01T00:00:00Z", "end_at": "2026-12-20T00:00:00Z"},
     "enrollments": [{"type": "student", "computed_current_score": 87.5, "computed_current_grade": "B"}]},
    {"id": 2, "name": "Bases de Datos", "term": {"name": "Q4 2026", "start_at": "2026-10-01T00:00:00Z", "end_at": "2026-12-20T00:00:00Z"},
     "enrollments": [{"type": "student", "computed_current_score": None}]},
    {"id": 3, "name": "Curso viejo", "term": {"name": "Q2 2026", "start_at": "2026-04-01T00:00:00Z", "end_at": "2026-06-20T00:00:00Z"}},
    {"id": 4},  # sin nombre (acceso restringido)
]


def cliente(rutas):
    return ClienteCanvas("T", sesion=SesionFalsa(rutas))


def test_cursos_periodo_y_promedio(monkeypatch):
    import app.canvas_api as api

    class Fecha(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 5, 12, 0, tzinfo=tz or UTC)

    monkeypatch.setattr(api, "datetime", Fecha)
    cursos, termino = cliente({"/users/self/courses": Resp(CURSOS)}).cursos()
    assert termino == "Q4 2026"
    assert [c.nombre for c in cursos] == ["Redes", "Bases de Datos"]
    assert cursos[0].promedio == 87.5 and cursos[0].nota == "B" and cursos[1].promedio is None


def test_notas_y_anuncios():
    graded = [
        {"id": 1, "score": 95, "grade": "95", "graded_at": "2026-10-20T10:00:00Z", "course_id": 1,
         "assignment": {"name": "Lab 1", "points_possible": 100, "html_url": "/courses/1/assignments/5"}},
        {"id": 2, "score": 8, "graded_at": "2026-10-22T10:00:00Z", "course_id": 1,
         "assignment": {"name": "Quiz 2", "points_possible": 10}},
        {"id": 3, "score": None, "grade": None, "course_id": 1, "assignment": {"name": "Sin nota"}},
    ]
    anun = [{"id": 9, "title": "Cambio de aula", "message": "<p>Ahora en B-2</p>", "posted_at": "2026-10-24T10:00:00Z",
             "context_code": "course_1", "html_url": "https://x/a"}]
    c = cliente({"/graded_submissions": Resp(graded), "/announcements": Resp(anun)})
    notas = c.notas({"1": "Redes"})
    assert [n.titulo for n in notas] == ["Quiz 2", "Lab 1"] and notas[1].texto == "95 / 100" and notas[0].materia == "Redes"
    a = c.anuncios({"1": "Redes"})
    assert a[0].texto == "Ahora en B-2" and a[0].materia == "Redes"


def test_servicio_guarda_cursos_y_cae_a_actividad(tmp_path):
    entregada_domingo = {"plannable_type": "assignment", "plannable_id": 50, "context_name": "Redes", "html_url": "/c/50",
                         "plannable": {"id": 50, "title": "Ya entregada esta semana", "due_at": "2026-10-26T04:00:00Z"},
                         "submissions": {"submitted": True}}
    rutas = {"/planner/items": Resp(PLANNER + [entregada_domingo]), "/users/self/courses": Resp([CURSOS[0]]), "/activity_stream": Resp(ACTIVIDAD)}
    ses = SesionFalsa(rutas)

    class Cred:
        def obtener(self, n):
            return {"token": "T", "ical_url": None}[n]

    s = Servicio(Almacen(tmp_path), Cred(), lambda t: ClienteCanvas(t, sesion=ses), leer_tareas=lambda: {})
    r = s.refrescar(AHORA)
    assert [c.nombre for c in r.cursos] == ["Redes"] and r.termino == "Q4 2026"
    # /announcements y /graded_submissions no existen (404): se usan los datos de la actividad
    assert r.anuncios and r.anuncios[0].titulo == "Cambio de aula"
    assert r.notas and r.notas[0].texto == "95"
    assert r.entregadas_semana == 1  # la del domingo 25 (22:00 hora de Honduras); la del lunes ya es otra semana
    # y quedan guardados para la proxima vez que no haya internet
    ses.rutas["/planner/items"] = requests.ConnectionError("x")
    off = s.refrescar(AHORA)
    assert off.sin_conexion and off.cursos and off.notas and off.anuncios and off.termino == "Q4 2026"


def test_ical_deduce_cursos(tmp_path):
    from test_logica import ICS
    from app import ical

    class Cred:
        def obtener(self, n):
            return {"token": None, "ical_url": "https://ical"}[n]

    s = Servicio(Almacen(tmp_path), Cred(), lector_ical=lambda u: ical.parsear(ICS), leer_tareas=lambda: {})
    r = s.refrescar(datetime(2026, 10, 30, 12, 0, tzinfo=UTC))
    assert sorted(c.nombre for c in r.cursos) == ["Ingeniería de Software", "Redes"]


# ---------- tareas: hecha / silenciar / posponer / repetir ----------
def test_silenciada_o_hecha_no_recibe_recordatorios():
    n = {}
    p = [pend("a", 0.5), pend("b", 0.5)]
    r = recordatorios.calcular(p, AHORA, n, omitir=lambda x: x.id == "a")
    assert [x.pendiente.id for x in r] == ["b"]


def test_posponer_y_repetir(tmp_path):
    t = EstadoTareas(tmp_path)
    p = pend("a", 10)
    t.posponer("a", AHORA + timedelta(minutes=30))
    assert t.avisos_programados([p], AHORA + timedelta(minutes=29)) == []
    assert [m for _, m in t.avisos_programados([p], AHORA + timedelta(minutes=31))] == ["posponida"]
    assert t.avisos_programados([p], AHORA + timedelta(minutes=32)) == []  # sin repetir el aviso
    t.repetir("a", 120, AHORA)
    assert t.avisos_programados([p], AHORA + timedelta(minutes=119)) == []
    assert [m for _, m in t.avisos_programados([p], AHORA + timedelta(minutes=121))] == ["repeticion"]
    assert t.avisos_programados([p], AHORA + timedelta(minutes=200)) == []
    assert [m for _, m in t.avisos_programados([p], AHORA + timedelta(minutes=242))] == ["repeticion"]
    # al vencer deja de repetir
    assert t.avisos_programados([p], AHORA + timedelta(hours=11)) == [] and t.repetir_min("a") == 0


def test_silenciada_no_avisa_y_se_recuerda_al_reabrir(tmp_path):
    t = EstadoTareas(tmp_path)
    t.posponer("a", AHORA)
    t.silenciar("a")
    assert t.avisos_programados([pend("a", 5)], AHORA + timedelta(hours=1)) == []
    t2 = EstadoTareas(tmp_path)  # "cerrar y abrir la app"
    assert t2.silenciada("a") and not t2.hecha("a")
    t2.silenciar("a", False)
    t2.marcar_hecha("a")
    assert EstadoTareas(tmp_path).hecha("a")


def test_limpiar_olvida_tareas_que_ya_no_existen(tmp_path):
    t = EstadoTareas(tmp_path)
    t.marcar_hecha("a"); t.marcar_hecha("b")
    t.limpiar({"a"})
    assert EstadoTareas(tmp_path).d.keys() == {"a"}


# ---------- resumen ----------
def test_semana_y_resumen():
    assert resumen.limites_semana(AHORA)[0].isoformat() == "2026-10-19"
    p = [pend("hoy", 3), pend("manana", 20), pend("vieja", -5), pend("sig_semana", 24 * 5)]
    est = resumen.estadisticas(p, lambda i: i == "manana", entregadas_semana=2, ahora=AHORA)
    assert [x.id for x in est["hoy"]] == ["hoy"] and [x.id for x in est["vencidas"]] == ["vieja"]
    # semana lun 19 - dom 25: solo cuentan 'hoy' y 'vieja' (+2 entregadas); 'manana' ya es lunes 26
    assert est["semana_total"] == 4 and est["semana_hechas"] == 2 and est["semana_faltan"] == 2
    titulo, msg = resumen.texto_resumen(est)
    assert "Hoy vence 1: Tarea hoy." in msg and "faltan 2 de 4" in msg and "1 vencida" in msg


def test_resumen_sin_nada():
    est = resumen.estadisticas([], lambda i: False, 0, AHORA)
    assert resumen.texto_resumen(est)[1] == "Hoy no vence nada. Esta semana no tienes entregas."


# ---------- geometria ----------
PANT = (0, 0, 1920, 1080)


def test_expande_hacia_arriba_si_esta_abajo_a_la_izquierda():
    rect, ancla = geometria.expandir((20, 1000, 70, 70), (360, 520), PANT)
    assert ancla == "bl" and rect == (20, 550, 360, 520)
    assert geometria.contraer(rect, ancla, (70, 70)) == (20, 1000)


def test_expande_hacia_abajo_y_a_la_izquierda_si_esta_arriba_a_la_derecha():
    rect, ancla = geometria.expandir((1830, 20, 70, 70), (360, 520), PANT)
    assert ancla == "tr" and rect == (1540, 20, 360, 520)
    assert geometria.contraer(rect, ancla, (70, 70)) == (1830, 20)


def test_no_se_sale_de_la_pantalla():
    rect, _ = geometria.expandir((0, 500, 70, 70), (360, 700), (0, 0, 1000, 800))
    assert rect[1] >= 0 and rect[1] + rect[3] <= 800


def test_pegar_a_borde():
    assert geometria.pegar_a_borde((10, 500), (70, 70), PANT) == (4, 500)
    assert geometria.pegar_a_borde((1845, 1000), (70, 70), PANT) == (1846, 1006)
    assert geometria.pegar_a_borde((500, 500), (70, 70), PANT) == (500, 500)


# ---------- ajustes ----------
def test_ajustes_persisten(tmp_path):
    a = Ajustes(tmp_path)
    a["escala"] = 1.25; a["pos"] = [10, 20]
    a.guardar()
    b = Ajustes(tmp_path)
    assert b["escala"] == 1.25 and b["pos"] == [10, 20] and b["resumen_activo"] is True


# ---------- inicio con Windows (registro simulado) ----------
class RegFalso:
    HKEY_CURRENT_USER, KEY_READ, KEY_SET_VALUE, REG_SZ = "HKCU", 1, 2, 1

    def __init__(self):
        self.valores = {}

    def OpenKey(self, raiz, ruta, _r, _acc):
        assert raiz == "HKCU" and ruta.endswith(r"CurrentVersion\Run")
        reg = self

        class K:
            def __enter__(s): return s
            def __exit__(s, *a): return False
        return K()

    def SetValueEx(self, k, nombre, _r, _t, valor): self.valores[nombre] = valor
    def QueryValueEx(self, k, nombre):
        if nombre not in self.valores:
            raise FileNotFoundError
        return self.valores[nombre], 1
    def DeleteValue(self, k, nombre):
        if nombre not in self.valores:
            raise FileNotFoundError
        del self.valores[nombre]


def test_inicio_con_windows():
    r = RegFalso()
    assert not inicio_windows.activo(r)
    inicio_windows.activar(r)
    assert inicio_windows.activo(r)
    cmd = r.valores["CanvasWidget"]
    assert cmd.startswith('"') and cmd.endswith('lanzar.pyw"')
    inicio_windows.desactivar(r)
    assert not inicio_windows.activo(r)
    inicio_windows.desactivar(r)  # no falla si ya no esta
