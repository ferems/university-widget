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


def normalizar_url(texto: str) -> str:
    """Deja solo https://dominio (sin rutas). Lanza ValueError con un mensaje claro si no sirve."""
    t = (texto or "").strip()
    if not t:
        raise ValueError("Escribe la dirección de tu Canvas, por ejemplo https://tu-universidad.instructure.com")
    if "://" not in t:
        t = "https://" + t
    partes = urlsplit(t)
    if partes.scheme != "https":
        raise ValueError("La dirección debe empezar con https:// (conexión segura).")
    host = partes.hostname or ""
    if not re.fullmatch(r"[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+", host):
        raise ValueError("Esa dirección no parece válida. Ejemplo: https://tu-universidad.instructure.com")
    return f"https://{host}" + (f":{partes.port}" if partes.port else "")


def url_canvas(carpeta: Path = DATOS) -> str:
    """Sitio de Canvas configurado (o el de config.py). Solo lectura: la puede usar el hilo de actualizacion."""
    d = json_local.leer(Path(carpeta) / "ajustes.json", {})
    try:
        return normalizar_url(d.get("url_canvas") or "") if isinstance(d, dict) and d.get("url_canvas") else URL_CANVAS
    except ValueError:
        return URL_CANVAS
