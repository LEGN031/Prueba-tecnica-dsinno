from lectura import cargar_y_normalizar_csv
from state.estado import inicializar_bd, obtener_cuenta, guardar_resultado
from api import consultar_api
from config.config import API_URL_BASE, API_TIMEOUT, API_MAX_RETRIES, API_BACKOFF_FACTOR, PATH_INPUT_CSV, PATH_OUTPUT_EXCEL, PATH_DB_STATE, PATH_LOG_FILE
import sqlite3
from pathlib import Path
from openpyxl import Workbook
from contextlib import closing


def procesar_cuentas():
    inicializar_bd()

    cuentas = cargar_y_normalizar_csv(PATH_INPUT_CSV)

    for id_cuenta, info in cuentas.items():
        estado_actual = obtener_cuenta(id_cuenta)

        if estado_actual in ("OK", "NO_EXISTE", "INVALIDO"):
            continue

        if not info["es_valido"]:
            resultado = {
                "estado": "INVALIDO",
                "causa": "Formato no numerico",
                "intentos": 0,
                "title": None,
                "userId": None,
                "body": None
            }
            guardar_resultado(id_cuenta, resultado, info["veces_en_archivo"])
            continue

        resultado = consultar_api(id_cuenta,API_URL_BASE)
        
        guardar_resultado(id_cuenta, resultado, info["veces_en_archivo"])

if __name__ == "__main__":

    procesar_cuentas()

    