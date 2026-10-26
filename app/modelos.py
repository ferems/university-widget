from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional


def leer_fecha_iso(texto: str) -> datetime:
    """Convierte '2026-10-30T05:59:00Z' en fecha con zona horaria (UTC)."""
    texto = texto.strip()
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    dt = datetime.fromisoformat(texto)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class Pendiente:
    id: str
    titulo: str
    materia: str
    vence: datetime
    url: str
    entregada: Optional[bool] = None  # None = no se sabe (modo iCal)

    def a_dict(self) -> dict:
        return {
            "id": self.id,
            "titulo": self.titulo,
            "materia": self.materia,
            "vence": self.vence.astimezone(timezone.utc).isoformat(),
            "url": self.url,
            "entregada": self.entregada,
        }

    @staticmethod
    def de_dict(d: dict) -> "Pendiente":
        return Pendiente(
            id=d["id"],
            titulo=d["titulo"],
            materia=d.get("materia", ""),
            vence=leer_fecha_iso(d["vence"]),
            url=d.get("url", ""),
            entregada=d.get("entregada"),
        )


@dataclass
class Actividad:
    clave: str      # identificador unico para no avisar dos veces
    tipo: str       # 'anuncio' | 'calificacion' | 'mensaje'
    titulo: str
    materia: str
    detalle: str
    url: str
    fecha: str = ""


@dataclass
class Curso:
    id: str
    nombre: str
    codigo: str = ""
    promedio: Optional[float] = None   # porcentaje actual, si Canvas lo informa
    nota: str = ""

    def a_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def de_dict(d: dict) -> "Curso":
        return Curso(**d)


@dataclass
class Anuncio:
    id: str
    titulo: str
    materia: str
    texto: str
    fecha: str
    url: str

    def a_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def de_dict(d: dict) -> "Anuncio":
        return Anuncio(**d)


@dataclass
class Nota:
    id: str
    titulo: str
    materia: str
    texto: str      # por ejemplo "95 / 100"
    fecha: str
    url: str

    def a_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def de_dict(d: dict) -> "Nota":
        return Nota(**d)


@dataclass
class Aviso:
    tipo: str       # 'anuncio' | 'calificacion' | 'mensaje' | 'tarea'
    titulo: str
    mensaje: str
    url: str


@dataclass
class Recordatorio:
    clave: str
    nivel: str      # '24h' | '3h' | '1h' | 'vencida'
    pendiente: Pendiente
    titulo: str
    mensaje: str
