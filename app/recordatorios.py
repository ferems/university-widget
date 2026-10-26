"""Decide que recordatorios toca enviar (sin duplicados)."""
from __future__ import annotations

from datetime import datetime
from typing import Callable, List, MutableMapping, Optional

from . import formato
from .config import DIAS_ATRAS, UMBRALES_HORAS
from .modelos import Pendiente, Recordatorio


def calcular(pendientes: List[Pendiente], ahora: datetime, notificados: MutableMapping[str, bool],
             omitir: Optional[Callable[[Pendiente], bool]] = None) -> List[Recordatorio]:
    """Devuelve los recordatorios nuevos y los anota en `notificados` (se modifica)."""
    salida: List[Recordatorio] = []
    for p in pendientes:
        if p.entregada is True or (omitir and omitir(p)):
            continue
        base = f"{p.id}|{p.vence.isoformat()}"
        resta = p.vence - ahora
        horas = resta.total_seconds() / 3600
        if horas > 0:
            aplicables = [h for h in UMBRALES_HORAS if horas <= h]
            if not aplicables:
                continue
            elegido = min(aplicables)  # si abrimos la app tarde, solo el mas urgente
            clave = f"{base}|{elegido}h"
            ya_avisado = clave in notificados
            for h in aplicables:
                notificados[f"{base}|{h}h"] = True
            if ya_avisado:
                continue
            salida.append(Recordatorio(
                clave=clave, nivel=f"{elegido}h", pendiente=p,
                titulo=f"Entrega {formato.cuenta(resta)}",
                mensaje=f"{p.titulo}" + (f" · {p.materia}" if p.materia else ""),
            ))
        elif p.entregada is False and -horas <= DIAS_ATRAS * 24:
            clave = f"{base}|vencida"
            if clave in notificados:
                continue
            notificados[clave] = True
            salida.append(Recordatorio(
                clave=clave, nivel="vencida", pendiente=p,
                titulo="Tarea vencida",
                mensaje=f"{p.titulo}" + (f" · {p.materia}" if p.materia else ""),
            ))
    return salida
