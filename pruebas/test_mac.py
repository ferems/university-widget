"""Pruebas de las piezas para Mac (se simula la plataforma; no hace falta una Mac)."""
import plistlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import inicio_auto, notificaciones  # noqa: E402


def test_inicio_en_mac_crea_y_quita_el_launchagent(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert inicio_auto.disponible()
    assert not inicio_auto.activo(tmp_path)
    inicio_auto.activar(tmp_path)
    assert inicio_auto.activo(tmp_path)
    datos = plistlib.loads(inicio_auto.archivo_mac(tmp_path).read_bytes())
    assert datos["Label"] == inicio_auto.ETIQUETA_MAC
    assert datos["RunAtLoad"] is True
    assert datos["ProgramArguments"][1].endswith("lanzar.pyw")
    inicio_auto.desactivar(tmp_path)
    assert not inicio_auto.activo(tmp_path)
    inicio_auto.desactivar(tmp_path)  # no falla si ya no esta


def test_launchagent_escapa_rutas_raras(monkeypatch):
    monkeypatch.setattr(inicio_auto, "RAIZ", Path("/Users/ana/Mis & <Cosas>/widget"))
    datos = plistlib.loads(inicio_auto.contenido_plist().encode())
    assert "Mis & <Cosas>" in datos["WorkingDirectory"]


def test_notificacion_mac_no_pega_el_texto_en_el_codigo():
    peligroso = 'hola" & do shell script "echo x'
    cmd = notificaciones.comando_mac("Titulo", peligroso)
    assert cmd[0] == "osascript"
    assert cmd[-2:] == [peligroso, "Titulo"]          # van como argumentos, aparte del script
    assert all(peligroso not in parte for parte in cmd[:-2])


def test_notificacion_mac_llama_a_osascript(monkeypatch):
    llamadas = []
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(notificaciones.subprocess, "run", lambda cmd, **kw: llamadas.append(cmd))
    notificaciones.Notificador().enviar("Hola", "Tienes una tarea")
    assert llamadas and llamadas[0][0] == "osascript"


def test_si_osascript_falla_usa_la_bandeja(monkeypatch):
    mensajes = []

    class Bandeja:
        def showMessage(self, t, m):
            mensajes.append((t, m))

    def falla(*a, **k):
        raise OSError("sin osascript")

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(notificaciones.subprocess, "run", falla)
    notificaciones.Notificador(Bandeja()).enviar("Hola", "Mensaje")
    assert mensajes == [("Hola", "Mensaje")]
