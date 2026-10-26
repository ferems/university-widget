#!/bin/bash
# College Widget para Mac: haz doble clic (o ejecuta "bash iniciar.command").
# La primera vez prepara todo solo; despues solo abre el widget.
cd "$(dirname "$0")" || exit 1

if [ -x ".venv/bin/python" ]; then
    nohup .venv/bin/python -m app >/dev/null 2>&1 &
    exit 0
fi

# Busca un Python 3.11 o mas nuevo.
PYEXE=""
for candidato in python3 python3.13 python3.12 python3.11 \
    /opt/homebrew/bin/python3 /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3; do
    ruta="$(command -v "$candidato" 2>/dev/null)"
    [ -z "$ruta" ] && continue
    if "$ruta" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        PYEXE="$ruta"
        break
    fi
done

if [ -z "$PYEXE" ]; then
    echo
    echo "No encontre Python 3.11 o más nuevo."
    echo "Instálalo desde https://www.python.org/downloads/macos/ y abre este archivo otra vez."
    open "https://www.python.org/downloads/macos/" 2>/dev/null
    read -r -p "Presiona Enter para cerrar..." _
    exit 1
fi

echo "Preparando College Widget por primera vez. Esto tarda un par de minutos..."
"$PYEXE" -m venv .venv || { echo "No se pudo crear el entorno de Python."; read -r -p "Presiona Enter para cerrar..." _; exit 1; }
.venv/bin/python -m pip install --upgrade pip
if ! .venv/bin/python -m pip install -r requirements.txt; then
    echo
    echo "Falló la instalación de los componentes. Revisa tu internet y abre este archivo otra vez."
    rm -rf .venv
    read -r -p "Presiona Enter para cerrar..." _
    exit 1
fi

nohup .venv/bin/python -m app >/dev/null 2>&1 &
exit 0
