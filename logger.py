"""
logger.py
---------
Módulo centralizado de logging para el proceso de cuentas médicas.

Responsabilidades:
  - Configurar un logger con RotatingFileHandler (archivo) y StreamHandler (consola).
  - Exponer la función `imprimir_resumen` que calcula y registra las métricas
    de la corrida a partir de la base de datos SQLite de estado.

Integración:
    from logger import configurar_logger, imprimir_resumen
    logger = configurar_logger()
"""

import logging
import sqlite3
from logging.handlers import RotatingFileHandler
from pathlib import Path
from contextlib import closing

from config.config import PATH_LOG_FILE, PATH_DB_STATE

# ---------------------------------------------------------------------------
# Constantes internas
# ---------------------------------------------------------------------------
_LOG_FORMAT = "%(asctime)s [%(levelname)s] [ID: %(threadName)s] %(message)s"
_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_MAX_BYTES = 5 * 1024 * 1024   # 5 MB por archivo de log
_BACKUP_COUNT = 3               # Hasta 3 archivos de respaldo rotados


# ---------------------------------------------------------------------------
# Configuración del logger
# ---------------------------------------------------------------------------

def configurar_logger(
    nombre: str = "proceso_cuentas",
    nivel: int = logging.DEBUG,
) -> logging.Logger:
    """
    Configura y devuelve un logger con doble destino:

    - **RotatingFileHandler**: escribe en ``config.PATH_LOG_FILE`` con
      rotación automática (5 MB, 3 respaldos). Crea la carpeta si no existe.
    - **StreamHandler**: muestra los mismos registros en la consola (stdout).

    Niveles de uso recomendado
    ~~~~~~~~~~~~~~~~~~~~~~~~~~
    - ``INFO``    → Avances generales (inicio, fin, ID procesado con éxito).
    - ``WARNING`` → Registros ignorados, duplicados o formatos inválidos.
    - ``ERROR``   → Fallos definitivos tras agotar reintentos o errores críticos.

    Args:
        nombre: Nombre del logger (default: ``"proceso_cuentas"``).
        nivel:  Nivel mínimo de captura (default: ``logging.DEBUG``).

    Returns:
        Instancia configurada de :class:`logging.Logger`.
    """
    logger = logging.getLogger(nombre)

    # Evita añadir handlers duplicados si la función se llama más de una vez.
    if logger.handlers:
        return logger

    logger.setLevel(nivel)

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_LOG_DATE_FORMAT)

    # --- Handler de archivo con rotación -----------------------------------
    log_path = Path(PATH_LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(nivel)
    file_handler.setFormatter(formatter)

    # --- Handler de consola ------------------------------------------------
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(nivel)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


# ---------------------------------------------------------------------------
# Resumen de ejecución
# ---------------------------------------------------------------------------

def imprimir_resumen(
    total_filas_csv: int,
    total_omitidos: int,
    db_path: str = PATH_DB_STATE,
) -> None:
    """
    Calcula y registra (consola + archivo de log) el resumen de la corrida.

    Las métricas se obtienen directamente de la base de datos SQLite para
    garantizar consistencia con el estado real persistido.

    Métricas reportadas
    ~~~~~~~~~~~~~~~~~~~
    - Total de filas leídas del CSV vs. total de IDs únicos procesados.
    - Cuentas resueltas con éxito (``OK``).
    - Cuentas fallidas, desglosadas por causa:
        * ``NO_EXISTE``    → HTTP 404.
        * ``INVALIDO``     → Formato no numérico.
        * ``ERROR_TECNICO``→ Timeouts o 5xx agotados.
    - Registros omitidos en esta corrida (ya resueltos previamente).

    Args:
        total_filas_csv: Número total de filas de datos leídas del archivo CSV
                         (sin contar la cabecera ni líneas vacías).
        total_omitidos:  Número de IDs saltados en esta corrida porque ya
                         tenían estado definitivo en la BD.
        db_path:         Ruta a la base de datos SQLite de estado.
                         Por defecto usa ``config.PATH_DB_STATE``.
    """
    logger = logging.getLogger("proceso_cuentas")

    # -- Consultas a la BD --------------------------------------------------
    conteos: dict[str, int] = {
        "OK": 0,
        "NO_EXISTE": 0,
        "INVALIDO": 0,
        "ERROR_TECNICO": 0,
        "OTRO": 0,
    }
    total_unicos_bd = 0

    try:
        with closing(sqlite3.connect(db_path)) as conn:
            cursor = conn.cursor()

            # Total de IDs únicos en BD
            cursor.execute("SELECT COUNT(*) FROM cuentas")
            total_unicos_bd = cursor.fetchone()[0]

            # Conteo por estado
            cursor.execute(
                "SELECT estado, COUNT(*) FROM cuentas GROUP BY estado"
            )
            for estado, cantidad in cursor.fetchall():
                if estado in conteos:
                    conteos[estado] = cantidad
                else:
                    conteos["OTRO"] += cantidad

    except sqlite3.Error as exc:
        # Error crítico: no se puede leer la BD para el resumen.
        logger.error("No se pudo leer la base de datos para el resumen: %s", exc)
        return

    # -- Construcción del resumen -------------------------------------------
    total_fallidos = conteos["NO_EXISTE"] + conteos["INVALIDO"] + conteos["ERROR_TECNICO"]

    separador = "=" * 60
    lineas = [
        separador,
        "         RESUMEN DE EJECUCIÓN",
        separador,
        f"  Filas leídas del CSV (sin cabecera) : {total_filas_csv}",
        f"  IDs únicos registrados en BD        : {total_unicos_bd}",
        separador,
        f"  ✔  Resueltas con éxito  (OK)        : {conteos['OK']}",
        separador,
        "  Cuentas con fallos:",
        f"     • NO_EXISTE    (HTTP 404)         : {conteos['NO_EXISTE']}",
        f"     • INVALIDO     (formato inválido) : {conteos['INVALIDO']}",
        f"     • ERROR_TECNICO (timeout / 5xx)   : {conteos['ERROR_TECNICO']}",
        f"     TOTAL fallidas                    : {total_fallidos}",
        separador,
        f"  ↷  Omitidas esta corrida (ya resueltas): {total_omitidos}",
        separador,
    ]

    for linea in lineas:
        logger.info(linea)

