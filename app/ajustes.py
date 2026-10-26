"""Preferencias del usuario (tamano, resumen diario, posicion). Solo las toca la ventana principal."""
from __future__ import annotations

from pathlib import Path

from . import json_local
from .config import DATOS

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
