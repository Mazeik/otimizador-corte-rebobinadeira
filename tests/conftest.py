import sys
from pathlib import Path

# Permite importar o pacote sem instalar (python -m pytest na raiz do projeto).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
