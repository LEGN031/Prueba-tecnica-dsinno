import os
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

API_URL_BASE = os.getenv("url_base", "https://jsonplaceholder.typicode.com/posts")
API_TIMEOUT = int(os.getenv("timeout", 5))
API_MAX_RETRIES = int(os.getenv("max_retries", 3))
API_BACKOFF_FACTOR = float(os.getenv("backoff_factor", 1.0))

PATH_INPUT_CSV = os.getenv("input_csv", "cuentas.csv")
PATH_OUTPUT_EXCEL = os.getenv("output_excel", "output/resultado.xlsx")
PATH_DB_STATE = os.getenv("db_state", "state/estado.db")
PATH_LOG_FILE = os.getenv("log_file", "logs/proceso.log")