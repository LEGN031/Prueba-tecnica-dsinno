from lectura import cargar_y_normalizar_csv
from state.estado import inicializar_bd, obtener_cuenta, guardar_resultado
from api import consultar_api
from config.config import (
    API_URL_BASE,
    API_TIMEOUT,
    API_MAX_RETRIES,
    API_BACKOFF_FACTOR,
    PATH_INPUT_CSV,
    PATH_OUTPUT_EXCEL,
    PATH_DB_STATE,
)
import sqlite3
from pathlib import Path
from openpyxl import Workbook
from contextlib import closing
from logger import configurar_logger, imprimir_resumen

logger = configurar_logger()

def exportar_excel(
    db_path=PATH_DB_STATE,
    tabla="cuentas",
    carpeta_salida=None
):
    if carpeta_salida is None:
        output_dir = Path(PATH_OUTPUT_EXCEL).parent
    else:
        output_dir = Path(carpeta_salida)

    output_dir.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(db_path)) as conexion:
        cursor = conexion.cursor()
        cursor.execute(f"SELECT * FROM {tabla}")
        columnas = [descripcion[0] for descripcion in cursor.description]
        registros = cursor.fetchall()

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Registros"
    hoja.append(columnas)

    for registro in registros:
        hoja.append(list(registro))

    ruta_archivo = Path(PATH_OUTPUT_EXCEL)
    libro.save(ruta_archivo)

    logger.info("Excel generado: %s (%d registros)", ruta_archivo, len(registros))
    print(f"Archivo generado correctamente: {ruta_archivo}")
    print(f"Total de registros exportados: {len(registros)}")

    return ruta_archivo

def procesar_cuentas():
    logger.info("Base de datos inicializada: %s", PATH_DB_STATE)
    inicializar_bd()

    cuentas = cargar_y_normalizar_csv(PATH_INPUT_CSV)

    total_filas_csv = sum(info["veces_en_archivo"] for info in cuentas.values())
    total_omitidos = 0

    logger.info(
        "CSV cargado: %d filas, %d IDs únicos — %s",
        total_filas_csv,
        len(cuentas),
        PATH_INPUT_CSV,
    )

    for id_cuenta, info in cuentas.items():
        if info["veces_en_archivo"] > 1:
            logger.warning(
                "ID duplicado en el archivo: aparece %d veces.",
                info["veces_en_archivo"],
            )

        estado_actual = obtener_cuenta(id_cuenta)

        if estado_actual in ("OK", "NO_EXISTE", "INVALIDO"):
            total_omitidos += 1
            logger.info("ID omitido (ya resuelto con estado '%s').", estado_actual)
            continue

        if not info["es_valido"]:
            logger.warning("ID con formato inválido detectado; se marcará como INVALIDO.")
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

        resultado = consultar_api(
            id_cuenta,
            API_URL_BASE,
            reintentos_maximos=API_MAX_RETRIES,
            backoff_factor=API_BACKOFF_FACTOR,
            timeout=API_TIMEOUT,
        )

        if resultado["estado"] == "OK":
            logger.info("ID procesado con éxito (OK) en %d intento(s).", resultado["intentos"])
        elif resultado["estado"] == "NO_EXISTE":
            logger.warning("ID no encontrado en la API (HTTP 404).")
        elif resultado["estado"] == "ERROR_TECNICO":
            logger.error(
                "Error técnico definitivo tras %d intento(s): %s",
                resultado["intentos"],
                resultado["causa"],
            )
        else:
            logger.warning("Estado inesperado recibido: %s.", resultado["estado"])

        guardar_resultado(id_cuenta, resultado, info["veces_en_archivo"])

    return total_filas_csv, total_omitidos

if __name__ == "__main__":
    logger.info("===== INICIO DEL PROCESO DE CUENTAS =====")

    total_filas, omitidos = procesar_cuentas()
    exportar_excel()
    imprimir_resumen(total_filas_csv=total_filas, total_omitidos=omitidos)

    logger.info("===== FIN DEL PROCESO DE CUENTAS =====")
