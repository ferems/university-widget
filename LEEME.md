# Canvas Widget

Un widget siempre visible que te avisa de tus pendientes de Canvas (CEUTEC / Unitec Honduras).
Solo **lee** tu Canvas: no entrega, envía ni modifica nada.

## Cómo abrirlo
1. Necesitas Python 3.11 o más nuevo en Windows (Microsoft Store: «Python 3.12», o python.org marcando **Add python.exe to PATH**).
2. Haz **doble clic en `iniciar.bat`**. La primera vez prepara todo solo (unos minutos, necesita internet).
3. Aparece un **ícono redondo** con un número rojo (tus pendientes) y un ícono azul con una "C" junto al reloj.
4. La primera vez te pide conectarte (ver abajo). Después ya no te lo vuelve a pedir.

## Iniciar con Windows
Abre el widget → ⚙ **Ajustes** → marca «Abrir el widget automáticamente al prender Windows» → Guardar.
(Crea una entrada solo para tu usuario; se quita desmarcando la misma casilla. Si cambias la carpeta `canvas-widget` de lugar, vuelve a marcarla.)

## Conectarte a Canvas (una sola vez)
Elige **una** opción en la ventana «Conectar con Canvas». Lo que pegues se guarda en el
**Administrador de credenciales de Windows**, nunca en un archivo.

- **Token de acceso (recomendado):** en Canvas, foto de perfil → Configuración → «Integraciones aprobadas» →
  «+ Nuevo token de acceso». Deja la fecha de vencimiento vacía y copia el token (solo se muestra una vez).
- **Enlace iCal (si no te deja crear tokens):** Calendario → «Fuente de calendario» → copia el enlace.
  Limitación: con iCal no se sabe si ya entregaste una tarea, y no hay promedios, notas ni anuncios.

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

## Avisos de Windows
- Recordatorios a las 24 h, 3 h y 1 h antes de cada entrega y cuando una tarea queda vencida. Cada uno llega una sola vez.
- Si falta menos de 1 hora: el ícono parpadea en rojo y sale una ventana grande encima de todo.
- Aviso cuando aparece una tarea, anuncio, calificación o mensaje nuevo.
- **Resumen diario** (por defecto 8:00 AM, se cambia en Ajustes): qué vence hoy y cuánto te falta de la semana.
  También está en el menú del ícono de la bandeja → «Resumen de la semana ahora».
- Sin internet: muestra los últimos datos guardados y lo dice en el panel; reintenta solo.

## Ícono de la bandeja (junto al reloj)
Clic = mostrar/ocultar. Clic derecho = menú (actualizar, resumen, probar notificación, ajustes, conexión, salir).

## Si algo falla
Mira `datos\registro.log` (no contiene tu token ni tu enlace).
