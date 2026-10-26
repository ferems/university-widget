"""Estado que TU decides por tarea: hecha, silenciada, posponer, recordar cada tanto."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from . import json_local
from .config import DATOS
from .modelos import Pendiente, leer_fecha_iso


def leer_estado(carpeta: Path = DATOS) -> dict:
    """Lectura sin modificar nada (la usa el hilo de actualizacion)."""
    d = json_local.leer(Path(carpeta) / "tareas.json", {})
    return d if isinstance(d, dict) else {}


class EstadoTareas:
    def __init__(self, carpeta: Path = DATOS):
        self.ruta = Path(carpeta) / "tareas.json"
        self.d: Dict[str, dict] = leer_estado(carpeta)

    # --- consultas ---
    def _t(self, id_: str) -> dict:
        return self.d.get(id_, {})

    def hecha(self, id_: str) -> bool:
        return bool(self._t(id_).get("hecha"))

    def silenciada(self, id_: str) -> bool:
        return bool(self._t(id_).get("silenciada"))

    def posponer_hasta(self, id_: str):
        h = self._t(id_).get("posponer_hasta")
        return leer_fecha_iso(h) if h else None

    def repetir_min(self, id_: str) -> int:
        return int(self._t(id_).get("repetir_min") or 0)

    # --- cambios ---
    def _set(self, id_: str, **campos) -> None:
        t = self.d.setdefault(id_, {})
        for k, v in campos.items():
            if v in (None, False, 0):
                t.pop(k, None)
            else:
                t[k] = v
        if not t:
            self.d.pop(id_, None)
        self.guardar()

    def marcar_hecha(self, id_: str, valor: bool = True) -> None:
        self._set(id_, hecha=valor)

    def silenciar(self, id_: str, valor: bool = True) -> None:
        self._set(id_, silenciada=valor)

    def posponer(self, id_: str, hasta: datetime) -> None:
        self._set(id_, posponer_hasta=hasta.astimezone(timezone.utc).isoformat())

    def repetir(self, id_: str, minutos: int, ahora: datetime) -> None:
        self._set(id_, repetir_min=minutos or None,
                  ultimo_repeticion=ahora.astimezone(timezone.utc).isoformat() if minutos else None)

    def guardar(self) -> None:
        json_local.escribir(self.ruta, self.d)

    # --- avisos programados por ti ---
    def avisos_programados(self, visibles: List[Pendiente], ahora: datetime) -> List[Tuple[Pendiente, str]]:
        """Devuelve (tarea, 'posponida'|'repeticion') que toca avisar ahora y lo anota."""
        salida: List[Tuple[Pendiente, str]] = []
        cambio = False
        for p in visibles:
            t = self.d.get(p.id)
            if not t or t.get("hecha") or t.get("silenciada"):
                continue
            hasta = t.get("posponer_hasta")
            if hasta and leer_fecha_iso(hasta) <= ahora:
                t.pop("posponer_hasta")
                salida.append((p, "posponida"))
                cambio = True
            cada = int(t.get("repetir_min") or 0)
            if cada:
                if p.vence <= ahora:  # ya vencio: deja de repetir
                    t.pop("repetir_min", None)
                    t.pop("ultimo_repeticion", None)
                    cambio = True
                else:
                    ult = leer_fecha_iso(t.get("ultimo_repeticion") or ahora.isoformat())
                    if ahora - ult >= timedelta(minutes=cada):
                        t["ultimo_repeticion"] = ahora.astimezone(timezone.utc).isoformat()
                        if not any(x[0] is p for x in salida):
                            salida.append((p, "repeticion"))
                        cambio = True
            if not t:
                self.d.pop(p.id, None)
        if cambio:
            self.guardar()
        return salida

    def limpiar(self, ids_conocidos: set) -> None:
        """Olvida tareas que ya no existen en Canvas (cuando hay datos recientes)."""
        viejos = [k for k in self.d if k not in ids_conocidos]
        if viejos:
            for k in viejos:
                self.d.pop(k)
            self.guardar()
