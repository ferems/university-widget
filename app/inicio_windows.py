"""Inicio automatico con Windows: una entrada del usuario actual en el registro (HKCU\\...\\Run).
No requiere permisos de administrador y se quita desde Ajustes."""
from __future__ import annotations

import sys
from pathlib import Path

from .config import RAIZ

RUTA = r"Software\Microsoft\Windows\CurrentVersion\Run"
NOMBRE = "CanvasWidget"


def _winreg(reg=None):
    if reg is not None:
        return reg
    import winreg  # solo existe en Windows
    return winreg


def comando() -> str:
    exe = Path(sys.executable)
    if exe.name.lower() == "python.exe":
        exe = exe.with_name("pythonw.exe")
    return f'"{exe}" "{RAIZ / "lanzar.pyw"}"'


def disponible(reg=None) -> bool:
    try:
        _winreg(reg)
        return True
    except ImportError:
        return False


def activo(reg=None) -> bool:
    try:
        r = _winreg(reg)
        with r.OpenKey(r.HKEY_CURRENT_USER, RUTA, 0, r.KEY_READ) as k:
            valor, _ = r.QueryValueEx(k, NOMBRE)
        return bool(valor)
    except (ImportError, OSError):
        return False


def activar(reg=None) -> None:
    r = _winreg(reg)
    with r.OpenKey(r.HKEY_CURRENT_USER, RUTA, 0, r.KEY_SET_VALUE) as k:
        r.SetValueEx(k, NOMBRE, 0, r.REG_SZ, comando())


def desactivar(reg=None) -> None:
    r = _winreg(reg)
    try:
        with r.OpenKey(r.HKEY_CURRENT_USER, RUTA, 0, r.KEY_SET_VALUE) as k:
            r.DeleteValue(k, NOMBRE)
    except FileNotFoundError:
        pass
