"""Plataformas de estudio. Canvas y Moodle se conectan por su API (tareas, cursos, notas, anuncios).
Las demas (Google Classroom, Blackboard, Brightspace, Schoology, Teams...) se conectan por el enlace de
calendario (iCal), que es lo unico que todas ofrecen al estudiante sin permisos especiales de la universidad."""

GUIAS_ICAL = {
    "Moodle": "Calendario → «Importar o exportar calendarios» → «Exportar calendario» → elige «Todos» y «Próximos 60 días» "
              "→ «Obtener URL del calendario».",
    "Google Classroom": "Las tareas de Classroom aparecen en Google Calendar. En calendar.google.com abre los ajustes del "
                        "calendario de la clase → «Dirección secreta en formato iCal».",
    "Brightspace (D2L)": "En el Calendario busca «Suscribirse» (o «Subscribe») y copia el enlace de la fuente.",
    "Blackboard": "En el Calendario busca la opción de fuente/suscripción (puede llamarse «Obtener fuente de calendario»). "
                  "Si tu universidad no la activó, no habrá enlace.",
    "Schoology": "Calendario → ícono de exportar → copia el enlace iCal.",
    "Outlook / Microsoft Teams": "Outlook en la web → Configuración → Calendario → Calendarios compartidos → «Publicar un "
                                 "calendario» → enlace ICS. Ojo: las tareas de Teams normalmente no salen en ese calendario.",
    "Canvas": "Calendario → «Fuente de calendario» (abajo a la derecha).",
}
