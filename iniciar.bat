@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title College Widget

rem ---- Python que se instala solo si no esta (version oficial de python.org) ----
set "PYVER=3.12.10"
set "PYURL=https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-amd64.exe"
set "PYSHA=67B5635E80EA51072B87941312D00EC8927C4DB9BA18938F7AD2D27B328B95FB"
set "PYEXE="

rem Si ya esta preparado, solo abre el widget.
if exist ".venv\Scripts\pythonw.exe" goto lanzar

call :buscar_python
set "PYEXE="
call :probar "py -3"
if not defined PYEXE call :probar "python"
if not defined PYEXE call :probar "python3"
if not defined PYEXE if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python313\python.exe"
if not defined PYEXE if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PYEXE if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python311\python.exe"
exit /b 0

:probar
rem Pregunta a Python donde esta; el falso "python" de la Microsoft Store no devuelve una ruta real.
for /f "usebackq delims=" %%E in (`%~1 -c "import sys;print(sys.executable if sys.version_info>=(3,11) else '')" 2^>nul`) do set "PYEXE=%%E"
if defined PYEXE if not exist "%PYEXE%" set "PYEXE="
exit /b 0


rem ======================================================================
:instalar_python
echo.
echo No encontre Python 3.11 o mas nuevo en esta computadora.
echo Puedo descargarlo del sitio oficial (python.org, unos 27 MB) e instalarlo
echo solo para tu usuario. No necesita permisos de administrador.
echo.
choice /c SN /m "Instalar Python ahora (S = si, N = no)"
if errorlevel 2 exit /b 1

set "TMPEXE=%TEMP%\python-%PYVER%-amd64.exe"
echo.
echo Descargando Python %PYVER% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -UseBasicParsing -Uri '%PYURL%' -OutFile '%TMPEXE%' } catch { exit 2 }; if ((Get-FileHash -Algorithm SHA256 -LiteralPath '%TMPEXE%').Hash -ne '%PYSHA%') { Remove-Item -LiteralPath '%TMPEXE%' -Force; exit 3 }"
if errorlevel 3 (
    echo El archivo descargado no coincide con el original de python.org. Por seguridad no se instalo.
    exit /b 1
)
if errorlevel 2 (
    echo No se pudo descargar. Revisa tu conexion a internet.
    exit /b 1
)

echo Instalando Python (puede tardar uno o dos minutos, no cierres esta ventana)...
start /wait "" "%TMPEXE%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1 Include_test=0 Include_doc=0
del /q "%TMPEXE%" 2>nul
call :buscar_python
exit /b 0
