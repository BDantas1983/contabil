import os
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path para importação de app
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.main import app

# Exporta para o handler Serverless da Vercel
application = app

