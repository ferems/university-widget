"""Notificaciones nativas de Windows (winotify). Si no estan disponibles, usa el globo de la bandeja."""
from __future__ import annotations

import logging
import sys

log = logging.getLogger(__name__)

try:  # solo existe en Windows
    from winotify import Notification, audio
except Exception:  # pragma: no cover
    Notification = None
    audio = None


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
        if self.bandeja is not None:
            self.bandeja.showMessage(titulo, mensaje)
