"""Datos guardados en disco (dentro de canvas-widget/datos): ultima lista de pendientes y
lo que ya se aviso. NO contiene credenciales."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .config import DATOS

_LIMITE = 1500


class Almacen:
    def __init__(self, carpeta: Path = DATOS):
        self.ruta = Path(carpeta) / "estado.json"

    def cargar(self) -> dict:
        base = {"pendientes": [], "actualizado": None, "fuente": "", "base_lista": False,
                "notificados": {}, "vistos_tareas": {}, "vistos_actividad": {}}
        try:
            base.update(json.loads(self.ruta.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
        return base

    def guardar(self, estado: dict) -> None:
        for clave in ("notificados", "vistos_tareas", "vistos_actividad"):
            d = estado.get(clave, {})
            if len(d) > _LIMITE:  # conserva lo mas reciente
                estado[clave] = dict(list(d.items())[-_LIMITE:])
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.ruta.with_suffix(".tmp")
        tmp.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.ruta)
