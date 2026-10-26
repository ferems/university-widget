"""Cliente de Canvas. SOLO LECTURA: unicamente hace peticiones GET."""
from __future__ import annotations

import html
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple
from urllib.parse import urljoin

import requests

from .config import URL_CANVAS
from .modelos import Actividad, Anuncio, Curso, Nota, Pendiente, leer_fecha_iso


class ErrorAutenticacion(Exception):
    """El token no sirve (vencido, mal copiado o revocado)."""


def _texto_plano(contenido: str, limite: int = 140) -> str:
    texto = html.unescape(re.sub(r"<[^>]+>", " ", contenido or ""))
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


class ClienteCanvas:
    def __init__(self, token: str, base: str = URL_CANVAS, sesion=None):
        self.base = base.rstrip("/")
        self.s = sesion or requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}"})

    # --- peticion GET con paginacion ---------------------------------
    def _get(self, ruta: str, params: dict | None = None):
        url = self.base + ruta
        resultados: list = []
        while url:
            r = self.s.get(url, params=params, timeout=20)
            params = None  # la URL "next" ya trae los parametros
            if r.status_code == 401:
                raise ErrorAutenticacion("Canvas rechazó el token (401).")
            r.raise_for_status()
            datos = r.json()
            if not isinstance(datos, list):
                return datos
            resultados.extend(datos)
            if len(resultados) > 2000:
                break
            url = r.links.get("next", {}).get("url")
        return resultados

    def _url(self, ruta: str) -> str:
        return urljoin(self.base + "/", ruta or "")

    # --- pendientes ---------------------------------------------------
    def planner_items(self, desde: datetime, hasta: datetime) -> List[Pendiente]:
        items = self._get(
            "/api/v1/planner/items",
            {"start_date": desde.date().isoformat(), "end_date": hasta.date().isoformat(), "per_page": 100},
        )
        salida: List[Pendiente] = []
        for it in items:
            tipo = it.get("plannable_type")
            if tipo not in ("assignment", "quiz", "discussion_topic"):
                continue
            plan = it.get("plannable") or {}
            override = it.get("planner_override") or {}
            if override.get("dismissed"):
                continue
            fecha = plan.get("due_at") or it.get("plannable_date")
            if not fecha:
                continue
            subs = it.get("submissions")
            entregada = None
            if isinstance(subs, dict):
                entregada = bool(subs.get("submitted") or subs.get("excused"))
            if override.get("marked_complete"):
                entregada = True
            ident = plan.get("id") or it.get("plannable_id")
            salida.append(
                Pendiente(
                    id=f"{tipo}-{ident}",
                    titulo=plan.get("title") or plan.get("name") or "(sin nombre)",
                    materia=it.get("context_name") or "",
                    vence=leer_fecha_iso(fecha),
                    url=self._url(it.get("html_url") or plan.get("html_url") or ""),
                    entregada=entregada,
                )
            )
        return salida

    def todo(self) -> List[Pendiente]:
        """Alternativa: lista 'Por hacer' de Canvas (solo lo no entregado)."""
        salida: List[Pendiente] = []
        for it in self._get("/api/v1/users/self/todo", {"per_page": 100}):
            tarea = it.get("assignment") or {}
            if not tarea.get("due_at"):
                continue
            salida.append(
                Pendiente(
                    id=f"assignment-{tarea.get('id')}",
                    titulo=tarea.get("name") or "(sin nombre)",
                    materia=it.get("context_name") or "",
                    vence=leer_fecha_iso(tarea["due_at"]),
                    url=self._url(tarea.get("html_url") or it.get("html_url") or ""),
                    entregada=False,
                )
            )
        return salida

    # --- cursos, periodo y promedios -------------------------------------
    def cursos(self) -> Tuple[List[Curso], str]:
        """Cursos activos del periodo vigente y el nombre del periodo (por ejemplo 'Q4 2026')."""
        datos = self._get("/api/v1/users/self/courses", {
            "enrollment_state": "active", "include[]": ["term", "total_scores"], "per_page": 100})
        ahora = datetime.now(timezone.utc)
        candidatos = []
        for c in datos:
            if "id" not in c or not (c.get("name") or c.get("course_code")):
                continue
            term = c.get("term") or {}
            ini = leer_fecha_iso(term["start_at"]) if term.get("start_at") else None
            fin = leer_fecha_iso(term["end_at"]) if term.get("end_at") else None
            vigente = (ini is None or ini <= ahora) and (fin is None or fin >= ahora)
            candidatos.append((c, term.get("name") or "", vigente))
        elegidos = [x for x in candidatos if x[2]] or candidatos
        cursos: List[Curso] = []
        for c, _, _ in elegidos:
            insc = next((e for e in (c.get("enrollments") or [])
                         if str(e.get("type", "")).lower() in ("student", "studentenrollment")), {})
            prom = insc.get("computed_current_score")
            cursos.append(Curso(str(c["id"]), c.get("name") or c.get("course_code"), c.get("course_code") or "",
                                float(prom) if prom is not None else None, insc.get("computed_current_grade") or ""))
        nombres = [t for _, t, _ in elegidos if t]
        termino = Counter(nombres).most_common(1)[0][0] if nombres else ""
        return cursos, termino

    # --- notas y anuncios ---------------------------------------------------
    def notas(self, cursos: Dict[str, str], limite: int = 10) -> List[Nota]:
        salida: List[Nota] = []
        for it in self._get("/api/v1/users/self/graded_submissions", {"include[]": ["assignment"], "per_page": 30}):
            tarea = it.get("assignment") or {}
            score, grade = it.get("score"), it.get("grade")
            if score is None and grade is None:
                continue
            total = tarea.get("points_possible")
            if score is not None and total:
                texto = f"{score:g} / {total:g}"
            else:
                texto = str(grade if grade is not None else score)
            salida.append(Nota(
                id=f"nota-{it.get('id')}", titulo=tarea.get("name") or "Tarea calificada",
                materia=cursos.get(str(it.get("course_id")), ""), texto=texto,
                fecha=it.get("graded_at") or it.get("submitted_at") or "",
                url=self._url(tarea.get("html_url") or it.get("preview_url") or "")))
        salida.sort(key=lambda n: n.fecha, reverse=True)
        return salida[:limite]

    def anuncios(self, cursos: Dict[str, str], limite: int = 15) -> List[Anuncio]:
        if not cursos:
            return []
        ahora = datetime.now(timezone.utc)
        items = self._get("/api/v1/announcements", {
            "context_codes[]": [f"course_{i}" for i in cursos],
            "start_date": (ahora - timedelta(days=45)).date().isoformat(),
            "end_date": (ahora + timedelta(days=1)).date().isoformat(),
            "active_only": "true", "per_page": 50})
        salida: List[Anuncio] = []
        for it in items:
            codigo = str(it.get("context_code", "")).replace("course_", "")
            salida.append(Anuncio(
                id=f"anuncio-{it.get('id')}", titulo=it.get("title") or "Anuncio",
                materia=cursos.get(codigo, ""), texto=_texto_plano(it.get("message"), 200),
                fecha=it.get("posted_at") or it.get("created_at") or "", url=it.get("html_url") or ""))
        salida.sort(key=lambda a: a.fecha, reverse=True)
        return salida[:limite]

    # --- actividad nueva ---------------------------------------------

    def actividad(self, cursos: Dict[str, str]) -> List[Actividad]:
        salida: List[Actividad] = []
        for it in self._get("/api/v1/users/self/activity_stream", {"per_page": 50}):
            tipo = it.get("type")
            materia = cursos.get(str(it.get("course_id")), "")
            ident = it.get("id")
            if tipo == "Announcement":
                salida.append(Actividad(f"anuncio-{ident}", "anuncio", it.get("title") or "Anuncio nuevo",
                                        materia, _texto_plano(it.get("message")), it.get("html_url") or "",
                                        it.get("created_at") or ""))
            elif tipo == "Submission" and (it.get("grade") is not None or it.get("score") is not None):
                nota = it.get("grade") if it.get("grade") is not None else it.get("score")
                salida.append(Actividad(f"nota-{ident}-{nota}", "calificacion", it.get("title") or "Calificación",
                                        materia, f"Nota: {nota}", it.get("html_url") or "",
                                        it.get("updated_at") or ""))
            elif tipo in ("Conversation", "Message"):
                salida.append(Actividad(f"mensaje-{ident}-{it.get('updated_at')}", "mensaje",
                                        it.get("title") or "Mensaje nuevo", materia,
                                        _texto_plano(it.get("message")), it.get("html_url") or "",
                                        it.get("updated_at") or ""))
        return salida
