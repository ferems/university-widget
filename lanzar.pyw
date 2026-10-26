"""Lanzador sin ventana negra (lo usa el inicio automatico de Windows)."""
import os
import sys
from pathlib import Path

raiz = Path(__file__).resolve().parent
os.chdir(raiz)
sys.path.insert(0, str(raiz))

from app.__main__ import main  # noqa: E402

sys.exit(main())
