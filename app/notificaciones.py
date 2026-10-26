"""Notificaciones nativas: Windows (winotify) y Mac (osascript). Si no hay, usa el globo de la bandeja."""
from __future__ import annotations

import logging
import subprocess
import sys

log = logging.getLogger(__name__)

try:  # solo existe en Windows
    from winotify import Notification, audio
except Exception:  # pragma: no cover
    Notification = None
    audio = None

# Texto fijo de AppleScript: el mensaje y el titulo llegan como argumentos, nunca pegados al codigo.
_SCRIPT_MAC = ("on run argv", "display notification (item 1 of argv) with title (item 2 of argv)", "end run")


def comando_mac(titulo: str, mensaje: str) -> list[str]:
    cmd = ["osascript"]
    for linea in _SCRIPT_MAC:
        cmd += ["-e", linea]
    return cmd + [mensaje[:250], titulo]


class Notificador:
    def __init__(self, bandeja=None):
        self.bandeja = bandeja

    def enviar(self, titulo: str, mensaje: str, url: str = "") -> None:
        if Notification is not None and sys.platform == "win32":
            try:
                n = Notification(app_id="College Widget", title=titulo, msg=mensaje[:250],
                                 duration="long", launch=url or "")
                n.set_audio(audio.Default, loop=False)
                n.show()
                return
            except Exception:
                log.exception("Fallo winotify; se usa la bandeja")
        if sys.platform == "darwin":
            try:
                subprocess.run(comando_mac(titulo, mensaje), check=True, timeout=10, capture_output=True)
                return
            except Exception:
                log.exception("Fallo la notificacion de Mac; se usa la bandeja")
        if self.bandeja is not None:
            self.bandeja.showMessage(titulo, mensaje)
