from lectura import cargar_y_normalizar_csv
from state.estado import inicializar_bd
from api import consultar_api
from config.config import API_URL_BASE, API_TIMEOUT, API_MAX_RETRIES, API_BACKOFF_FACTOR, PATH_INPUT_CSV, PATH_OUTPUT_EXCEL, PATH_DB_STATE, PATH_LOG_FILE


if __name__ == "__main__":


    cuentas = cargar_y_normalizar_csv(PATH_INPUT_CSV)
    

    invalidos = []
    validos = []
    for i in cuentas:
        if cuentas[i]['es_valido'] == True:
            validos.append(i)
        else:
            invalidos.append(i)
    
    response = consultar_api(id_cuenta=invalidos[0], url_base=API_URL_BASE, reintentos_maximos=API_MAX_RETRIES, backoff_factor=API_BACKOFF_FACTOR, timeout=API_TIMEOUT)
    


    print(cuentas)