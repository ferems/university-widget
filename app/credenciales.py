"""Guarda y lee el token / enlace iCal en el Administrador de credenciales de Windows (keyring).
Nunca se escriben en archivos ni en el codigo."""
from __future__ import annotations

from typing import Optional

import keyring

from .config import SERVICIO_KEYRING

TOKEN = "token"
ICAL = "ical_url"


def obtener(nombre: str) -> Optional[str]:
    try:
        valor = keyring.get_password(SERVICIO_KEYRING, nombre)
    except Exception:
        return None
    return valor or None


def guardar(nombre: str, valor: str) -> None:
    keyring.set_password(SERVICIO_KEYRING, nombre, valor.strip())


def borrar(nombre: str) -> None:
    try:
        keyring.delete_password(SERVICIO_KEYRING, nombre)
    except Exception:
        pass
