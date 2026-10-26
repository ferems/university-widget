@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Preparando Canvas Widget por primera vez. Esto tarda un par de minutos...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if not exist ".venv\Scripts\python.exe" (
        echo.
        echo No encontre Python. Instala Python 3.11 o mas nuevo desde https://www.python.org/downloads/
        echo y marca la casilla "Add python.exe to PATH" durante la instalacion.
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Fallo la instalacion de los componentes. Revisa tu internet y vuelve a abrir este archivo.
        pause
        exit /b 1
    )
)
start "" ".venv\Scripts\pythonw.exe" -m app
