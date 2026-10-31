import requests
import time
import random

def consultar_api(id_cuenta, url_base, reintentos_maximos=3, backoff_factor=1.0, timeout=5):
    url = f"{url_base}/{id_cuenta}"
    intentos = 0
    
    for intento in range(1, reintentos_maximos + 1):
        intentos = intento
        try:
            response = requests.get(url, timeout=timeout)
            
            # Caso 200
            if response.status_code == 200:
                data = response.json()
                return {
                    "estado": "OK",
                    "causa": "Exitoso",
                    "intentos": intentos,
                    "title": data.get("title"),
                    "userId": data.get("userId"),
                    "body": data.get("body")
                }
            
            # Caso 404
            elif response.status_code == 404:
                return {
                    "estado": "NO_EXISTE",
                    "causa": "HTTP 404 Not Found",
                    "intentos": intentos,
                    "title": None, "userId": None, "body": None
                }
            
            # Casos 400 a 499 menos 429
            elif 400 <= response.status_code < 500 and response.status_code != 429:
                return {
                    "estado": "ERROR_CLIENTE",
                    "causa": f"HTTP {response.status_code}",
                    "intentos": intentos,
                    "title": None, "userId": None, "body": None
                }
                
            # Casos 500
            else:
                causa = f"HTTP {response.status_code}"
                
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            causa = f"Error de conexion/timeout: {type(e).__name__}"

        if intento < reintentos_maximos:
            espera = (backoff_factor * (2 ** (intento - 1))) + random.uniform(0.1, 0.5)
            time.sleep(espera)

    return {
        "estado": "ERROR_TECNICO",
        "causa": f"Agotados {reintentos_maximos} intentos. Ultima causa: {causa}",
        "intentos": intentos,
        "title": None, "userId": None, "body": None
    }