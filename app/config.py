"""Ajustes generales (nada secreto aqui)."""
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"

URL_CANVAS = "https://unitechonduras.instructure.com"
ZONA = ZoneInfo("America/Tegucigalpa")

FUENTE = "Segoe UI" if sys.platform == "win32" else "Helvetica Neue"  # letra del sistema

INTERVALO_MINUTOS = 10     # revision automatica
DIAS_ADELANTE = 7          # lo que se muestra en la lista
DIAS_ATRAS = 3             # tareas vencidas recientes que aun se muestran
DIAS_DETECCION = 60        # ventana para detectar tareas nuevas
UMBRALES_HORAS = (24, 3, 1)
SERVICIO_KEYRING = "canvas-widget"
