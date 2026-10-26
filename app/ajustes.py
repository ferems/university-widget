"""Preferencias del usuario (tamano, resumen diario, posicion). Solo las toca la ventana principal."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

from . import json_local
from .config import DATOS, URL_CANVAS

ESCALAS = {"Pequeño": 0.85, "Normal": 1.0, "Grande": 1.25}

# (nombre, color) para elegir rapido
FONDOS = [("Noche", "#111827"), ("Negro", "#0a0a0a"), ("Azul oscuro", "#0f2547"), ("Verde oscuro", "#0f2e22"),
          ("Morado oscuro", "#2a1650"), ("Vino", "#3b1020"), ("Gris", "#374151")]
ICONOS = [("Azul", "#2563eb"), ("Morado", "#7c3aed"), ("Rosa", "#db2777"), ("Naranja", "#ea580c"),
          ("Turquesa", "#0891b2"), ("Verde", "#16a34a"), ("Gris", "#6b7280")]

BASE = {
    "escala": 1.0,
    "resumen_activo": True,
    "hora_resumen": "08:00",
    "ultimo_resumen": "",
    "url_canvas": "",           # vacio = la de config.py
    "plataforma": "",           # '' = automatico | 'canvas' | 'moodle' | 'ical'
    "url_moodle": "",
    "color_fondo": "#111827",
    "color_icono": "#2563eb",
    "dibujo_icono": "check",
    "pos": None,                # [x, y] del ícono
    "anuncios_vistos": [],
}


class Ajustes:
    def __init__(self, carpeta: Path = DATOS):
        self.ruta = Path(carpeta) / "ajustes.json"
        self.d = dict(BASE)
        datos = json_local.leer(self.ruta, {})
        if isinstance(datos, dict):
            self.d.update({k: v for k, v in datos.items() if k in BASE})

    def __getitem__(self, k):
        return self.d[k]

    def __setitem__(self, k, v):
        self.d[k] = v

    def guardar(self) -> None:
        self.d["anuncios_vistos"] = self.d["anuncios_vistos"][-300:]
        json_local.escribir(self.ruta, self.d)


def normalizar_url(texto: str, conservar_ruta: bool = False, nombre: str = "Canvas") -> str:
    """Deja solo https://dominio (sin rutas; con conservar_ruta se respeta una carpeta, como /moodle).
    Lanza ValueError con un mensaje claro si no sirve."""
    t = (texto or "").strip()
    if not t:
        raise ValueError(f"Escribe la dirección de tu {nombre}, por ejemplo https://tu-universidad.edu.hn")
    if "://" not in t:
        t = "https://" + t
    partes = urlsplit(t)
    if partes.scheme != "https":
        raise ValueError("La dirección debe empezar con https:// (conexión segura).")
    host = partes.hostname or ""
    if not re.fullmatch(r"[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+", host):
        raise ValueError("Esa dirección no parece válida. Ejemplo: https://tu-universidad.edu.hn")
    ruta = ""
    if conservar_ruta:
        ruta = partes.path.rstrip("/")
        if ruta and not re.fullmatch(r"(/[A-Za-z0-9._~-]+)+", ruta):
            raise ValueError("La carpeta de la dirección tiene caracteres raros. Ejemplo: https://campus.uni.edu.hn/moodle")
    return f"https://{host}" + (f":{partes.port}" if partes.port else "") + ruta


def _leer_ajuste(carpeta: Path, clave: str):
    d = json_local.leer(Path(carpeta) / "ajustes.json", {})
    return d.get(clave) if isinstance(d, dict) else None


def url_canvas(carpeta: Path = DATOS) -> str:
    """Sitio de Canvas configurado (o el de config.py). Solo lectura: la puede usar el hilo de actualizacion."""
    valor = _leer_ajuste(carpeta, "url_canvas")
    try:
        return normalizar_url(valor) if valor else URL_CANVAS
    except ValueError:
        return URL_CANVAS


def url_moodle(carpeta: Path = DATOS) -> str:
    """Sitio de Moodle configurado ('' si no hay)."""
    valor = _leer_ajuste(carpeta, "url_moodle")
    try:
        return normalizar_url(valor, True, "Moodle") if valor else ""
    except ValueError:
        return ""


def plataforma_elegida(carpeta: Path = DATOS) -> str:
    valor = _leer_ajuste(carpeta, "plataforma")
    return valor if valor in ("canvas", "moodle", "ical") else ""
