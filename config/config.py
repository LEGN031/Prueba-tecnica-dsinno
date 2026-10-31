import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables del archivo .env (soporta config/.env y .env en la raíz)
_directorio_actual = Path(__file__).resolve().parent
_env_en_config = _directorio_actual / ".env"
_env_en_raiz = _directorio_actual.parent / ".env"

if _env_en_config.exists():
    load_dotenv(dotenv_path=_env_en_config)
elif _env_en_raiz.exists():
    load_dotenv(dotenv_path=_env_en_raiz)
else:
    load_dotenv()

API_URL_BASE = os.getenv("url_base", "https://jsonplaceholder.typicode.com/posts")
API_TIMEOUT = int(os.getenv("timeout", 5))
API_MAX_RETRIES = int(os.getenv("max_retries", 3))
API_BACKOFF_FACTOR = float(os.getenv("backoff_factor", 1.0))

PATH_INPUT_CSV = os.getenv("input_csv", "cuentas.csv")
PATH_OUTPUT_EXCEL = os.getenv("output_excel", "output/resultado.xlsx")
PATH_DB_STATE = os.getenv("db_state", "state/estado.db")
PATH_LOG_FILE = os.getenv("log_file", "logs/proceso.log")
