import os

from dotenv import load_dotenv

load_dotenv()

LOGIN = os.getenv("CAPTURA_LOGIN")
SENHA = os.getenv("CAPTURA_SENHA")
BASE_URL = os.getenv("CAPTURA_BASE_URL", "https://apisbk.sbk.com.br/gtw/api-captura")

if not LOGIN or not SENHA:
    raise RuntimeError(
        "Variáveis de ambiente CAPTURA_LOGIN e CAPTURA_SENHA são obrigatórias. "
        "Defina-as no arquivo .env (veja .env.example)."
    )
