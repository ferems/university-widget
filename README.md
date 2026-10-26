# College Widget

Widget para Windows (y Mac, en prueba) que te avisa de tus pendientes de estudio: un ícono flotante con el número de tareas por entregar,
recordatorios del sistema (24 h, 3 h y 1 h antes), anuncios de tus docentes, calificaciones y promedios.
Hecho para estudiantes de CEUTEC / Unitec Honduras. Funciona con **cualquier Canvas**,
Moodle (con API completa: tareas, entregas, promedios, notas y anuncios) y, por calendario (iCal), con Google Classroom,
Blackboard, Brightspace, Schoology y cualquier otra que ofrezca un enlace de calendario.

- Ícono redondo con insignia que se expande hacia donde haya espacio, se pega a los bordes y se vuelve semitransparente.
- Pestañas: **Pendientes** (por día), **Cursos** (con promedio), **Anuncios** y **Notas**.
- Posponer, repetir o silenciar recordatorios por tarea; marcar tareas como hechas dentro del widget.
- Resumen diario de lo que vence hoy y esta semana.
- Ajustes: tamaño, colores, dibujo del ícono e inicio automático.

## Privacidad y seguridad
- **Solo lectura:** únicamente hace peticiones GET a Canvas; no entrega, envía ni modifica nada.
- Tu token (o enlace iCal) se guarda en el **Administrador de credenciales de Windows** (o el **Llavero** de macOS), nunca en archivos ni en el código.
- Tus tareas y ajustes se guardan solo en tu PC, en la carpeta `datos/` (que no se sube a GitHub).
- No hay servidores intermedios: la app habla directamente con tu Canvas.
- Proyecto independiente: no está afiliado ni respaldado por Instructure ni por tu universidad.

## Instalación (Windows 10/11)
1. Descarga este proyecto (botón verde **Code → Download ZIP**) y descomprímelo donde quieras.
2. Haz doble clic en **`iniciar.bat`**. Si no tienes Python, **te pregunta y lo instala solo** (versión oficial de python.org,
   verificada, solo para tu usuario y sin permisos de administrador). Luego instala sus componentes. La primera vez tarda unos minutos y necesita internet.
3. Cuando te lo pida, elige tu plataforma y pega tu acceso (ver abajo).

## Conectarte a tu plataforma
- **Canvas con token (recomendado):** muestra tareas, cursos, promedios, notas y anuncios. En Canvas: foto de perfil → Configuración →
  «Integraciones aprobadas» → «+ Nuevo token de acceso». En la ventana de conexión escribe también la dirección de tu Canvas.
- **Moodle con token:** en Moodle: tu perfil → Preferencias → Claves de seguridad → «Moodle mobile web service». Escribe también la
  dirección de tu Moodle. Muestra tareas (y si ya entregaste), cursos, promedios, notas y anuncios. *Probado con respuestas simuladas;
  no se ha probado contra un Moodle real, así que si algo falla avísanos.*
- **Otra plataforma con calendario (iCal):** busca en su calendario «Exportar», «Suscribirse» o «Fuente» y pega el enlace.
  Moodle: Calendario → Importar o exportar calendarios → Exportar calendario → Obtener URL. Google Classroom: «Dirección secreta en formato iCal»
  del calendario de la clase. Con este modo solo se leen las fechas (no hay notas, promedios ni anuncios), pero los eventos que se repiten sí se expanden.

Más detalles de uso en [LEEME.md](LEEME.md).

## UNAH y UNICAH (Moodle)
Ambas universidades hondureñas usan Moodle según sus páginas oficiales y notas de prensa. Se conectan con la opción **Moodle** (dirección de tu aula virtual + clave
«Moodle mobile web service» en Preferencias → Claves de seguridad), o con el calendario (iCal) si esa clave no está activada. *No se ha probado con cuentas reales de estas universidades.*
Pasos detallados en [LEEME.md](LEEME.md).

## Instalación en Mac (en prueba)
Necesitas Python 3.11 o más nuevo (https://www.python.org/downloads/macos/). Descarga el ZIP, abre Terminal y ejecuta `bash iniciar.command`
arrastrando el archivo a la ventana (el ZIP no conserva el permiso de ejecución; si haces `chmod +x iniciar.command` una vez, ya abre con doble clic).
Las notificaciones usan el centro de notificaciones de macOS y el inicio automático crea un LaunchAgent en `~/Library/LaunchAgents`.
Esta versión no se ha probado en una Mac real; si algo falla, abre un *issue* con el contenido de `datos/registro.log`.

## Android
No hay versión para Android: este programa está hecho con Python y ventanas de escritorio, y Android necesita una app distinta.



## Usarlo con otro Canvas (otra universidad)
No hace falta tocar código: en la ventana «Conexión…» escribe la dirección de tu Canvas (por ejemplo `https://tu-universidad.instructure.com`).
Solo se aceptan direcciones `https://` y el token solo se envía a esa dirección. La zona horaria (`ZONA`) y la dirección predeterminada están en `app/config.py`.

## Pruebas
```
.venv\Scripts\python -m pip install pytest
.venv\Scripts\python -m pytest pruebas
```
