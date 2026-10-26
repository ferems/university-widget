"""Une todo: descarga datos, detecta novedades y calcula recordatorios. No usa ventanas."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import requests

from . import credenciales, ical, recordatorios, tareas
from .almacen import Almacen
from .canvas_api import ClienteCanvas, ErrorAutenticacion
from .config import DIAS_ADELANTE, DIAS_ATRAS, DIAS_DETECCION
from .modelos import Anuncio, Aviso, Curso, Nota, Pendiente, Recordatorio
from .resumen import en_semana

# errores "de forma" de respuestas secundarias: se ignoran sin tumbar la actualizacion
_TOLERABLES = (requests.HTTPError, ValueError, KeyError, TypeError, AttributeError)


@dataclass
class Resultado:
    pendientes: List[Pendiente] = field(default_factory=list)
    avisos: List[Aviso] = field(default_factory=list)
    recordatorios: List[Recordatorio] = field(default_factory=list)
    cursos: List[Curso] = field(default_factory=list)
    anuncios: List[Anuncio] = field(default_factory=list)
    notas: List[Nota] = field(default_factory=list)
    termino: str = ""
    entregadas_semana: int = 0
    sin_conexion: bool = False
    error: Optional[str] = None
    sin_credenciales: bool = False
    fuente: str = ""
    actualizado: Optional[datetime] = None


def _seguro(fn, defecto):
    try:
        return fn()
    except _TOLERABLES:
        return defecto


class Servicio:
    def __init__(self, almacen: Almacen | None = None, cred=credenciales, cliente_fabrica=ClienteCanvas,
                 lector_ical=ical.leer, leer_tareas=tareas.leer_estado):
        self.almacen = almacen or Almacen()
        self.cred = cred
        self.cliente_fabrica = cliente_fabrica
        self.lector_ical = lector_ical
        self.leer_tareas = leer_tareas

    # --- ultimo estado guardado --------------------------------------
    def desde_cache(self, **extra) -> Resultado:
        est = self.almacen.cargar()
        act = datetime.fromisoformat(est["actualizado"]) if est.get("actualizado") else None
        return Resultado(
            pendientes=[Pendiente.de_dict(d) for d in est["pendientes"]],
            cursos=[Curso.de_dict(d) for d in est.get("cursos", [])],
            anuncios=[Anuncio.de_dict(d) for d in est.get("anuncios", [])],
            notas=[Nota.de_dict(d) for d in est.get("notas", [])],
            termino=est.get("termino", ""), entregadas_semana=est.get("entregadas_semana", 0),
            fuente=est.get("fuente", ""), actualizado=act, **extra,
        )

    # --- descarga ------------------------------------------------------
    def _descargar(self, token, enlace, ahora):
        if token:
            try:
                c = self.cliente_fabrica(token)
                desde, hasta = ahora - timedelta(days=DIAS_ATRAS), ahora + timedelta(days=DIAS_DETECCION)
                try:
                    pend = c.planner_items(desde, hasta)
                except requests.HTTPError:
                    pend = c.todo()
                cursos, termino = _seguro(c.cursos, ([], ""))
                mapa = {x.id: x.nombre for x in cursos}
                act = _seguro(lambda: c.actividad(mapa), [])
                anuncios = _seguro(lambda: c.anuncios(mapa), None)
                if anuncios is None:
                    anuncios = [Anuncio(a.clave, a.titulo, a.materia, a.detalle, a.fecha, a.url)
                                for a in act if a.tipo == "anuncio"]
                notas = _seguro(lambda: c.notas(mapa), None)
                if notas is None:
                    notas = [Nota(a.clave, a.titulo, a.materia, a.detalle.replace("Nota: ", ""), a.fecha, a.url)
                             for a in act if a.tipo == "calificacion"]
                return pend, act, "api", dict(cursos=cursos, termino=termino, anuncios=anuncios, notas=notas)
            except ErrorAutenticacion:
                if not enlace:
                    raise
        return self.lector_ical(enlace), [], "ical", {}

    def refrescar(self, ahora: datetime | None = None) -> Resultado:
        ahora = ahora or datetime.now(timezone.utc)
        token, enlace = self.cred.obtener(credenciales.TOKEN), self.cred.obtener(credenciales.ICAL)
        if not token and not enlace:
            return self.desde_cache(sin_credenciales=True)
        try:
            todos, actividad, fuente, extras = self._descargar(token, enlace, ahora)
        except (requests.ConnectionError, requests.Timeout):
            return self.desde_cache(sin_conexion=True)
        except ErrorAutenticacion:
            return self.desde_cache(error="Canvas no aceptó el token guardado. Vuelve a conectar (Conexión…).")
        except requests.RequestException as e:
            return self.desde_cache(error=f"Canvas respondió con un error ({type(e).__name__}). Se muestran los últimos datos.")

        est = self.almacen.cargar()
        avisos: List[Aviso] = []

        # --- novedades (la primera vez solo se "memoriza", sin avisar) ---
        primera = not est["base_lista"]
        for p in todos:
            if p.entregada is True:
                continue
            if p.id not in est["vistos_tareas"]:
                est["vistos_tareas"][p.id] = True
                if not primera:
                    avisos.append(Aviso("tarea", "Tarea nueva", f"{p.titulo}" + (f" · {p.materia}" if p.materia else ""), p.url))
        for a in actividad:
            if a.clave not in est["vistos_actividad"]:
                est["vistos_actividad"][a.clave] = True
                if not primera:
                    etiqueta = {"anuncio": "Anuncio nuevo", "calificacion": "Nueva calificación", "mensaje": "Mensaje nuevo"}[a.tipo]
                    cuerpo = " · ".join(x for x in (a.titulo, a.materia, a.detalle) if x)
                    avisos.append(Aviso(a.tipo, etiqueta, cuerpo, a.url))
        est["base_lista"] = True

        # --- lo que se muestra: vencidas recientes + proximos dias ---
        minimo = ahora - timedelta(days=DIAS_ATRAS)
        maximo = ahora + timedelta(days=DIAS_ADELANTE)
        visibles = [p for p in todos if p.entregada is not True and minimo <= p.vence <= maximo]
        if fuente == "ical":  # sin saber si se entrego, lo ya vencido no se muestra
            visibles = [p for p in visibles if p.vence >= ahora]
        visibles.sort(key=lambda p: p.vence)
        entregadas_semana = sum(1 for p in todos if p.entregada is True and en_semana(p.vence, ahora))

        # --- cursos: sin API se deducen de las tareas ---
        cursos = extras.get("cursos") or []
        if not cursos:
            nombres = sorted({p.materia for p in todos if p.materia})
            cursos = [Curso(n, n) for n in nombres]

        ts = self.leer_tareas()
        omitir = lambda p: bool(ts.get(p.id, {}).get("silenciada") or ts.get(p.id, {}).get("hecha"))  # noqa: E731
        recs = recordatorios.calcular(visibles, ahora, est["notificados"], omitir)

        est.update({
            "pendientes": [p.a_dict() for p in visibles], "actualizado": ahora.isoformat(), "fuente": fuente,
            "cursos": [c.a_dict() for c in cursos], "termino": extras.get("termino", ""),
            "entregadas_semana": entregadas_semana,
        })
        if fuente == "api":
            est["anuncios"] = [a.a_dict() for a in extras["anuncios"]]
            est["notas"] = [n.a_dict() for n in extras["notas"]]
        self.almacen.guardar(est)
        return Resultado(
            pendientes=visibles, avisos=avisos, recordatorios=recs, cursos=cursos,
            anuncios=[Anuncio.de_dict(d) for d in est.get("anuncios", [])],
            notas=[Nota.de_dict(d) for d in est.get("notas", [])],
            termino=est["termino"], entregadas_semana=entregadas_semana, fuente=fuente, actualizado=ahora)
