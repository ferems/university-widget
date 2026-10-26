"""Cliente de Moodle (Web Services). SOLO LECTURA: unicamente se llaman funciones de consulta (lista blanca).
El token se obtiene en Moodle: tu perfil → Preferencias → Claves de seguridad → «Moodle mobile web service»."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

import requests

from ..ajustes import url_moodle
from ..canvas_api import ErrorAutenticacion, _texto_plano
from ..modelos import Actividad, Anuncio, Curso, Nota, Pendiente

# Unicas funciones permitidas: todas son de consulta.
FUNCIONES_LECTURA = frozenset({
    "core_webservice_get_site_info", "core_enrol_get_users_courses", "gradereport_overview_get_course_grades",
    "core_calendar_get_action_events_by_timesort", "mod_assign_get_submission_status",
    "mod_forum_get_forums_by_courses", "mod_forum_get_forum_discussions", "mod_forum_get_forum_discussions_paginated",
    "gradereport_user_get_grade_items",
})
_CODIGOS_TOKEN = {"invalidtoken", "accessexception", "invalidlogin"}


class ClienteMoodle:
    def __init__(self, token: str, base: str | None = None, sesion=None):
        self.base = (base or url_moodle()).rstrip("/")
        if not self.base:
            raise ErrorAutenticacion("Falta la dirección de tu Moodle.")
        self.token = token
        self.s = sesion or requests.Session()
        self._uid: int | None = None

    def _llamar(self, funcion: str, **params):
        if funcion not in FUNCIONES_LECTURA:
            raise ValueError(f"Función no permitida (solo lectura): {funcion}")
        # POST solo para que el token no quede en la URL; son consultas, no cambian nada en Moodle.
        datos = {"wstoken": self.token, "wsfunction": funcion, "moodlewsrestformat": "json"}
        for k, v in params.items():
            if isinstance(v, (list, tuple)):
                for i, x in enumerate(v):
                    datos[f"{k}[{i}]"] = x
            else:
                datos[k] = v
        r = self.s.post(self.base + "/webservice/rest/server.php", data=datos, timeout=25)
        r.raise_for_status()
        js = r.json()
        if isinstance(js, dict) and js.get("exception"):
            if js.get("errorcode") in _CODIGOS_TOKEN:
                raise ErrorAutenticacion("Moodle rechazó el token.")
            raise ValueError(f"Moodle: {js.get('errorcode') or js.get('exception')}")
        return js

    def usuario(self) -> int:
        if self._uid is None:
            self._uid = int(self._llamar("core_webservice_get_site_info")["userid"])
        return self._uid

    def _enlace(self, ruta: str) -> str:
        return ruta if ruta.startswith("http") else self.base + "/" + ruta.lstrip("/")

    # --- cursos y promedios -------------------------------------------------
    def cursos(self) -> Tuple[List[Curso], str]:
        ahora = datetime.now(timezone.utc).timestamp()
        lista = self._llamar("core_enrol_get_users_courses", userid=self.usuario())
        vigentes = [c for c in lista if (not c.get("enddate") or c["enddate"] >= ahora)
                    and (not c.get("startdate") or c["startdate"] <= ahora + 86400) and not c.get("hidden")]
        vigentes = vigentes or list(lista)
        notas: Dict[int, float] = {}
        try:
            for g in self._llamar("gradereport_overview_get_course_grades", userid=self.usuario()).get("grades", []):
                try:
                    notas[int(g["courseid"])] = float(g["rawgrade"])
                except (KeyError, TypeError, ValueError):
                    pass
        except (requests.HTTPError, ValueError):
            pass
        cursos = [Curso(str(c["id"]), c.get("fullname") or c.get("shortname") or "Curso", c.get("shortname") or "",
                        notas.get(int(c["id"]))) for c in vigentes]
        return cursos, ""

    # --- pendientes ------------------------------------------------------------
    def pendientes(self, desde: datetime, hasta: datetime) -> List[Pendiente]:
        js = self._llamar("core_calendar_get_action_events_by_timesort", timesortfrom=int(desde.timestamp()),
                          timesortto=int(hasta.timestamp()), limitnum=50)
        salida: List[Pendiente] = []
        for ev in js.get("events", []):
            if not ev.get("timesort") or not ev.get("name"):
                continue
            entregada = None
            if ev.get("modulename") == "assign" and ev.get("instance"):
                entregada = self._entregada(ev["instance"])
            curso = (ev.get("course") or {}).get("fullname") or ""
            salida.append(Pendiente(
                id=f"moodle-{ev.get('id')}", titulo=ev["name"], materia=curso,
                vence=datetime.fromtimestamp(ev["timesort"], timezone.utc),
                url=self._enlace(ev.get("url") or ev.get("viewurl") or ""), entregada=entregada))
        return salida

    def _entregada(self, id_tarea) -> bool | None:
        try:
            estado = self._llamar("mod_assign_get_submission_status", assignid=id_tarea)
        except (requests.HTTPError, ValueError):
            return None
        sub = ((estado.get("lastattempt") or {}).get("submission") or {})
        if sub.get("status") == "submitted":
            return True
        if sub:
            return False
        return None

    # --- anuncios y notas ------------------------------------------------------
    def anuncios(self, cursos: Dict[str, str], limite: int = 15) -> List[Anuncio]:
        if not cursos:
            return []
        foros = self._llamar("mod_forum_get_forums_by_courses", courseids=[int(i) for i in cursos])
        salida: List[Anuncio] = []
        for f in foros:
            if f.get("type") != "news":
                continue
            try:
                js = self._llamar("mod_forum_get_forum_discussions", forumid=f["id"], perpage=5)
            except ValueError:
                js = self._llamar("mod_forum_get_forum_discussions_paginated", forumid=f["id"], perpage=5)
            for d in js.get("discussions", []):
                salida.append(Anuncio(
                    id=f"anuncio-{d.get('discussion') or d.get('id')}", titulo=d.get("name") or d.get("subject") or "Anuncio",
                    materia=cursos.get(str(f.get("course")), ""), texto=_texto_plano(d.get("message"), 200),
                    fecha=datetime.fromtimestamp(d.get("timemodified") or d.get("created") or 0, timezone.utc).isoformat(),
                    url=self._enlace(f"mod/forum/discuss.php?d={d.get('discussion') or d.get('id')}")))
        salida.sort(key=lambda a: a.fecha, reverse=True)
        return salida[:limite]

    def notas(self, cursos: Dict[str, str], limite: int = 10) -> List[Nota]:
        salida: List[Nota] = []
        for cid, nombre in cursos.items():
            js = self._llamar("gradereport_user_get_grade_items", courseid=int(cid), userid=self.usuario())
            for ug in js.get("usergrades", []):
                for it in ug.get("gradeitems", []):
                    cuando, bruta = it.get("gradedategraded"), it.get("graderaw")
                    if it.get("itemtype") != "mod" or not cuando or bruta is None:
                        continue
                    maximo = it.get("grademax")
                    texto = f"{bruta:g} / {maximo:g}" if maximo else str(it.get("gradeformatted") or bruta)
                    salida.append(Nota(
                        id=f"nota-{cid}-{it.get('id')}-{bruta}", titulo=it.get("itemname") or "Actividad calificada",
                        materia=nombre, texto=texto,
                        fecha=datetime.fromtimestamp(cuando, timezone.utc).isoformat(),
                        url=self._enlace(f"course/view.php?id={cid}")))
        salida.sort(key=lambda n: n.fecha, reverse=True)
        return salida[:limite]

    # --- paquete completo para el servicio -----------------------------------------
    def descargar(self, ahora: datetime, dias_atras: int, dias_adelante: int):
        pend = self.pendientes(ahora - timedelta(days=dias_atras), ahora + timedelta(days=dias_adelante))
        cursos, termino = self.cursos()
        mapa = {c.id: c.nombre for c in cursos}

        def seguro(fn):
            try:
                return fn()
            except (requests.HTTPError, ValueError, KeyError, TypeError, AttributeError):
                return []

        anuncios = seguro(lambda: self.anuncios(mapa))
        notas = seguro(lambda: self.notas(mapa))
        act = [Actividad(a.id, "anuncio", a.titulo, a.materia, a.texto, a.url, a.fecha) for a in anuncios]
        act += [Actividad(f"{n.id}", "calificacion", n.titulo, n.materia, f"Nota: {n.texto}", n.url, n.fecha) for n in notas]
        return pend, act, "api", dict(cursos=cursos, termino=termino, anuncios=anuncios, notas=notas)
