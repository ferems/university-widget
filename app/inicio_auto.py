"""Inicio automatico al encender la computadora, igual para Windows y Mac.

- Windows: entrada del usuario en el registro (ver inicio_windows.py).
- Mac: un archivo "LaunchAgent" en ~/Library/LaunchAgents (solo del usuario actual, sin administrador).
Se activa y se quita desde Ajustes. Linux no esta soportado."""
from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

from . import inicio_windows
from .config import RAIZ

ETIQUETA_MAC = "com.collegewidget.app"


def _es_mac() -> bool:
    return sys.platform == "darwin"


def _es_windows() -> bool:
    return sys.platform == "win32"


def archivo_mac(carpeta: Path | None = None) -> Path:
    base = Path(carpeta) if carpeta is not None else Path.home() / "Library" / "LaunchAgents"
    return base / f"{ETIQUETA_MAC}.plist"


def contenido_plist() -> str:
    python = escape(sys.executable)
    lanzador = escape(str(RAIZ / "lanzar.pyw"))
    raiz = escape(str(RAIZ))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{ETIQUETA_MAC}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>{lanzador}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{raiz}</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""


def disponible() -> bool:
    return _es_mac() or inicio_windows.disponible()


def activo(carpeta_mac: Path | None = None) -> bool:
    if _es_mac():
        return archivo_mac(carpeta_mac).exists()
    return inicio_windows.activo()


def activar(carpeta_mac: Path | None = None) -> None:
    if _es_mac():
        ruta = archivo_mac(carpeta_mac)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido_plist(), encoding="utf-8")
        return
    inicio_windows.activar()


def desactivar(carpeta_mac: Path | None = None) -> None:
    if _es_mac():
        archivo_mac(carpeta_mac).unlink(missing_ok=True)
        return
    inicio_windows.desactivar()
