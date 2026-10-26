# College Widget

Un widget siempre visible que te avisa de tus pendientes de Canvas (CEUTEC / Unitec Honduras).
Solo **lee** tu Canvas: no entrega, envía ni modifica nada.

## Cómo abrirlo
1. Haz **doble clic en `iniciar.bat`**. Si no tienes Python (3.11 o más nuevo), el programa te pregunta y lo descarga e instala solo
   desde python.org (verifica que el archivo sea el original; no necesita administrador). La primera vez prepara todo (unos minutos, necesita internet).
2. Aparece un **ícono redondo** con un número rojo (tus pendientes) y un ícono azul con una "C" junto al reloj.
3. La primera vez te pide conectarte (ver abajo). Después ya no te lo vuelve a pedir.

## Cómo abrirlo en Mac (versión de prueba)
1. Necesitas **Python 3.11 o más nuevo** (si no lo tienes, instálalo desde https://www.python.org/downloads/macos/).
2. Abre la app **Terminal**, escribe `bash ` (con un espacio al final), arrastra el archivo `iniciar.command` a la ventana y presiona Enter.
   La primera vez prepara todo (unos minutos, necesita internet). Después también puedes darle doble clic a `iniciar.command`
   si antes escribiste una sola vez `chmod +x ` + arrastrar el archivo + Enter.
3. La primera vez macOS puede preguntar si permites notificaciones y si Python puede usar el llavero: di que **sí** para que funcionen los avisos y se guarde tu conexión.
4. El ícono aparece como un círculo flotante y también en la barra de menú de arriba.
*Esta versión se escribió sin tener una Mac para probarla: si algo falla, mira `datos/registro.log` y avísame.*

## Iniciar con la computadora
Abre el widget → ⚙ **Ajustes** → marca «Abrir el widget automáticamente al iniciar sesión en la computadora» → Guardar.
(En Windows crea una entrada solo para tu usuario; en Mac crea un archivo en `~/Library/LaunchAgents`. Se quita desmarcando la misma casilla. Si cambias la carpeta `canvas-widget` de lugar, vuelve a marcarla.)

## Conectarte a tu plataforma (una sola vez)
En la ventana «Conectar con tu plataforma» elige **una** opción. Lo que pegues se guarda en el
**Administrador de credenciales de Windows** (o el **Llavero** en Mac), nunca en un archivo. Para cambiarlo: botón **Conexión…** o clic derecho en el ícono de la bandeja.

- **Canvas — token de acceso (recomendado):** en Canvas, foto de perfil → Configuración → «Integraciones aprobadas» →
  «+ Nuevo token de acceso». Deja la fecha de vencimiento vacía y copia el token (solo se muestra una vez).
  Escribe también la dirección de tu Canvas (la de CEUTEC viene puesta). Así se ven tareas, cursos, promedios, notas y anuncios.
- **Moodle — token de acceso:** en Moodle, tu foto de perfil → Preferencias → Cuenta de usuario → «Claves de seguridad» → copia la
  clave de «Moodle mobile web service». Escribe también la dirección de tu Moodle. Se ven tareas (y si ya entregaste), cursos,
  promedios, notas y anuncios. Aviso: se probó con respuestas simuladas, no con un Moodle real. Si tu universidad no activó esa
  clave, usa la opción de calendario.
- **Otra plataforma — enlace de calendario (iCal):** busca en el calendario de tu plataforma «Exportar», «Suscribirse» o «Fuente / Feed».
  - Canvas: Calendario → «Fuente de calendario».
  - Moodle: Calendario → «Importar o exportar calendarios» → «Exportar calendario» → «Obtener URL del calendario».
  - Google Classroom: en Google Calendar, ajustes del calendario de la clase → «Dirección secreta en formato iCal».
  - Brightspace: Calendario → «Suscribirse». Schoology: Calendario → exportar. Blackboard: opción de fuente/suscripción del calendario
    (si tu universidad no la activó, no habrá enlace). Outlook/Teams: «Publicar un calendario» (las tareas de Teams normalmente no salen ahí).
  La ventana de conexión muestra estos pasos al elegir tu plataforma.

  Limitaciones: solo se leen las fechas del calendario; no hay notas, promedios ni anuncios, no se sabe si ya entregaste una tarea
  (por eso no avisa de «vencidas») y las clases o eventos que se repiten sí se muestran en cada fecha.

## UNAH y UNICAH (Moodle)
Según las páginas oficiales y notas de prensa que se revisaron, ambas universidades usan **Moodle**, así que se conectan con la opción **Moodle** de la ventana de conexión.
Esto **no se ha probado con una cuenta real** de ninguna de las dos; si algo falla, avisa.

1. Entra a tu aula virtual y copia la **dirección completa** que ves arriba en el navegador (hasta el `.hn` o `.edu`).
   - **UNAH:** documentos de la universidad dan como dirección `campusvirtual.unah.edu.hn`, pero pueden haberla cambiado; usa la que veas tú.
   - **UNICAH:** se entra desde unicah.edu con el botón **UNICAH ID** y luego el módulo de clases. La guía oficial no da la dirección: cópiala de tu navegador.
     (`unicah.neolms.com` es solo para Formación Continua, no para las carreras.)
2. En el widget: **Conexión…** → **Moodle** → escribe esa dirección.
3. En Moodle: tu foto de perfil → **Preferencias** → **Claves de seguridad** → copia la clave de «Moodle mobile web service» y pégala en el widget (nunca en un chat ni en un archivo).
4. Si esa clave **no aparece** (la universidad puede desactivarla; UNICAH además entra por un inicio de sesión único): usa la opción **Otra plataforma** con el enlace de calendario
   (Calendario → «Importar o exportar calendarios» → «Exportar calendario» → «Obtener URL»). Con eso solo verás fechas, sin notas, promedios ni anuncios.

## El ícono y el panel
- **Ícono redondo:** muestra cuántas tareas tienes pendientes. Se pone semitransparente cuando no lo usas.
  Arrástralo adonde quieras; si lo sueltas cerca de un borde de la pantalla, se **pega al borde**. Recuerda dónde lo dejaste.
- **Clic en el ícono:** se abre el panel. Crece **hacia arriba** si el ícono está abajo, hacia abajo si está arriba,
  y hacia la izquierda si está a la derecha. Para cerrarlo: botón ▾ o clic en la parte de arriba del panel.
- **Tamaño:** ⚙ Ajustes → Tamaño (Pequeño / Normal / Grande).

## Pestañas del panel
- **Pendientes:** agrupadas en Vencidas, Hoy, Mañana, Esta semana y Próxima semana. La barra de arriba muestra tu avance de la semana.
  - **Círculo a la izquierda:** marca la tarea como hecha (solo dentro del widget; no entrega nada en Canvas).
  - **Botón ⏰:** «Recordarme en…» (30 min, 1 h, 3 h, mañana 8:00 AM), «Recordarme cada…» (1 h, 3 h, 6 h, día),
    «Silenciar avisos de esta tarea» y «Marcar como hecha».
  - Clic en el nombre de una tarea: abre su página en Canvas.
- **Cursos:** tus cursos del periodo actual (por ejemplo Q4), cuáles tienen pendientes y el promedio de cada uno. Un clic en un curso filtra sus pendientes.
- **Anuncios:** los anuncios recientes de tus docentes (con un punto azul los que aún no abriste).
- **Notas:** el promedio por curso y tus últimas calificaciones.

## Avisos
- Recordatorios a las 24 h, 3 h y 1 h antes de cada entrega y cuando una tarea queda vencida. Cada uno llega una sola vez.
- Si falta menos de 1 hora: el ícono parpadea en rojo y sale una ventana grande encima de todo.
- Aviso cuando aparece una tarea, anuncio, calificación o mensaje nuevo.
- **Resumen diario** (por defecto 8:00 AM, se cambia en Ajustes): qué vence hoy y cuánto te falta de la semana.
  También está en el menú del ícono de la bandeja → «Resumen de la semana ahora».
- Sin internet: muestra los últimos datos guardados y lo dice en el panel; reintenta solo.

## Ícono de la bandeja (junto al reloj)
Clic = mostrar/ocultar. Clic derecho = menú (actualizar, resumen, probar notificación, ajustes, conexión, salir).

## Si algo falla
Mira `datos/registro.log` (no contiene tu token ni tu enlace).
