import os

from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CAPTURA_BASE_URL", "https://apisbk.sbk.com.br/gtw/api-captura")
PORTAL_URL = os.getenv("PORTAL_URL", "https://monitoramento.sbk.com.br/")
