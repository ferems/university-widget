# Canvas Widget

Widget para Windows que te avisa de tus pendientes de **Canvas**: un ícono flotante con el número de tareas por entregar,
recordatorios de Windows (24 h, 3 h y 1 h antes), anuncios de tus docentes, calificaciones y promedios.
Hecho para estudiantes de CEUTEC / Unitec Honduras, pero funciona con cualquier Canvas (ver más abajo).

- Ícono redondo con insignia que se expande hacia donde haya espacio, se pega a los bordes y se vuelve semitransparente.
- Pestañas: **Pendientes** (por día), **Cursos** (con promedio), **Anuncios** y **Notas**.
- Posponer, repetir o silenciar recordatorios por tarea; marcar tareas como hechas dentro del widget.
- Resumen diario de lo que vence hoy y esta semana.
- Ajustes: tamaño, colores, dibujo del ícono e inicio automático con Windows.

## Privacidad y seguridad
- **Solo lectura:** únicamente hace peticiones GET a Canvas; no entrega, envía ni modifica nada.
- Tu token (o enlace iCal) se guarda en el **Administrador de credenciales de Windows**, nunca en archivos ni en el código.
- Tus tareas y ajustes se guardan solo en tu PC, en la carpeta `datos/` (que no se sube a GitHub).
- No hay servidores intermedios: la app habla directamente con tu Canvas.
- Proyecto independiente: no está afiliado ni respaldado por Instructure ni por tu universidad.

## Instalación (Windows 10/11)
1. Instala **Python 3.11 o más nuevo** (Microsoft Store: «Python 3.12», o https://www.python.org/downloads/ marcando *Add python.exe to PATH*).
2. Descarga este proyecto (botón verde **Code → Download ZIP**) y descomprímelo donde quieras.
3. Haz doble clic en **`iniciar.bat`**. La primera vez instala sus componentes (unos minutos, necesita internet).
4. Cuando te lo pida, pega tu **token de acceso de Canvas** (Canvas → foto de perfil → Configuración → «Integraciones aprobadas» → «+ Nuevo token de acceso»)
   o, si tu universidad no lo permite, el **enlace de la Fuente de calendario** (Calendario → «Fuente de calendario»).

Más detalles de uso en [LEEME.md](LEEME.md).

## Usarlo con otro Canvas (otra universidad)
Abre `app/config.py` y cambia `URL_CANVAS` por la dirección de tu Canvas (por ejemplo `https://tu-universidad.instructure.com`).
La zona horaria está en la misma línea de ajustes (`ZONA`).

## Pruebas
```
.venv\Scripts\python -m pip install pytest
.venv\Scripts\python -m pytest pruebas
```
