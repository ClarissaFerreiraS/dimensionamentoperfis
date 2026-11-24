"""Ponto de entrada usado para empacotar o app com PyInstaller.

Existe porque `app/main.py` fica *dentro* do pacote `app`, e o PyInstaller
precisa de um script na raiz do projeto para que `import app.*` resolva
corretamente durante a análise de dependências.
"""

from __future__ import annotations

import sys

from app.main import main

if __name__ == "__main__":
    sys.exit(main())
