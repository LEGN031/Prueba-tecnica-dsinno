from urllib import response
from requests import request
from asyncio import timeout
from lectura import cargar_y_normalizar_csv
from state.estado import inicializar_bd
from api import consultar_api
import os
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()

    url = os.getenv("url_base")
    timeout = int(os.getenv("timeout"))
    reintentos_maximos = int(os.getenv("max_retries"))
    backoff_factor = float(os.getenv("backoff_factor"))

    csv = os.getenv("input_csv")


    cuentas = cargar_y_normalizar_csv(csv)
    

    invalidos = []
    validos = []
    for i in cuentas:
        if cuentas[i]['es_valido'] == True:
            validos.append(i)
        else:
            invalidos.append(i)
    
    response = consultar_api(id_cuenta=invalidos[0], url_base=url, reintentos_maximos=reintentos_maximos, backoff_factor=backoff_factor, timeout=timeout)
    


    print(cuentas)