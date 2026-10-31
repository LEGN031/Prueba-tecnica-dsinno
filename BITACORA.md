# BITÁCORA DE DESARROLLO ASISTIDO POR IA

Este documento (tambien desarrollado con apoyo de la IA) detalla de manera transparente y crítica la interacción con herramientas de Inteligencia Artificial durante la resolución del reto técnico, destacando aciertos, fallos identificados, decisiones de arquitectura tomadas de forma autónoma y lecciones aprendidas.

---

## 1. Herramienta de IA Utilizada y Alcance

- **Herramienta principal:** Antigravity IDE (modelos Claude 3.5 Sonnet / Gemini 3.8 Flash).
- **Áreas donde se utilizó la IA:**
  - **Estructuración y Boilerplate de Logging:** Generación de la configuración de `logging.handlers.RotatingFileHandler` y `StreamHandler`.
  - **Manejo de Reintentos HTTP:** Plantilla inicial del bucle de reintentos con cálculo de espera exponencial y captura de excepciones en `requests`.
  - **Consultas SQL de Agrupación:** Esqueleto de consultas SQL para calcular métricas agregadas (`GROUP BY estado`).

---

## 2. Prompts Clave Utilizados (Copiados tal cual)

Los siguientes prompts generaron valor real y aceleraron el desarrollo al estar bien acotados:

### Prompt 1: Configuración de Logging y Métricas
```text
Estoy desarrollando un script en Python para procesar un archivo CSV con cuentas médicas (cuentas.csv), consultar una API REST (JSONPlaceholder) y persistir el estado en una base de datos SQLite (estado.db).

Necesito implementar la capa de Logging y la función de Resumen de Ejecución siguiendo las buenas prácticas y las siguientes especificaciones:

1. Configuración de Logging:

Debe utilizar el módulo estándar logging con un handler RotatingFileHandler para escribir los registros en el archivo especificado en config.PATH_LOG_FILE (creando la carpeta de destino si no existe).

Debe incluir también un StreamHandler para mostrar los logs en la consola al mismo tiempo.

Formato del log: %(asctime)s [%(levelname)s] [ID: %(threadName)s] %(message)s.

Niveles de log requeridos:

INFO: Avances generales del proceso (inicio, fin, ID procesado con éxito).

WARNING: Registros ignorados, duplicados detectados o datos con formato inválido (abc).

ERROR: Fallos definitivos tras agotar reintentos técnicos o errores críticos de sistema.

2. Función de Resumen de Ejecución (imprimir_resumen):

Debe consultar la base de datos SQLite (state/estado.db) o recibir el estado de la corrida para calcular y mostrar las siguientes métricas agrupadas tanto en la consola como en el archivo de log:

Total de filas procesadas del archivo fuente vs. Total de IDs únicos.

Total de cuentas resueltas con éxito (OK).

Total de cuentas con fallos, desglosado por causa:

NO_EXISTE (HTTP 404).

INVALIDO (Formato no numérico).

ERROR_TECNICO (Timeouts o 5xx sin resolver).

Total de registros omitidos en la corrida por haber sido resueltos previamente.

3. Requisitos del Código:

Entrega el código modularizado (puedes estructurarlo en un archivo logger.py o dentro de main.py).

Asegúrate de que los logs no expongan datos sensibles innecesarios.

Devuelve el código formateado, documentado y listo para integrar con las variables cargadas desde el archivo de configuración config.py.
```
> **Por qué sirvió:** Estableció límites precisos sobre handlers, formato de cadena y métricas concretas a calcular, evitando respuestas genéricas.

---

## 3. Lo que la IA entregó mal o incompleto y cómo me di cuenta

### Caso 1: Bug sutil de flujo por identación del `return` (Crítico)
* **El fallo generado por la IA:** En la primera versión de `main.py`, la IA ubicó la instrucción `return total_filas_csv, total_omitidos` con **8 espacios de indentación**, es decir, dentro del cuerpo del bucle `for id_cuenta, info in cuentas.items():`.
* **Cómo me di cuenta:**
  - Al ejecutar `main.py` en una segunda corrida (cuando ya existían cuentas registradas en `estado.db`), los primeros registros ejecutaban `continue` por estar ya resueltos (`OK`, `NO_EXISTE`, `INVALIDO`).
  - Como el `return` estaba dentro del bucle pero detrás de ramas con `continue`, si todos los registros eran omitidos o se saltaban, el bucle terminaba naturalmente sin alcanzar la sentencia `return`.
  - Python devolvió implícitamente `None`, provocando el error en tiempo de ejecución:
    `TypeError: cannot unpack non-iterable NoneType object`.
* **Corrección aplicada:**
  - Se extrajo el `return` al nivel de indentación de la función (4 espacios) para asegurar que la tupla se retorne **siempre**, sin importar qué caminos tomen las iteraciones individuales.
  - Se añadió la acumulación explícita de `total_omitidos += 1` en la rama donde la cuenta ya existía en la BD.

### Caso 2: Import espurio introducido por autocompletado
* **El fallo:** La IA incluyó en la cabecera de `main.py` la línea `from Lib.asyncio.log import logger`, que colisionaba con el logger personalizado configurado en `logger.py`.
* **Cómo me di cuenta:** Revisión estática del código; un script síncrono que no usa `asyncio` no debe importar submódulos internos de la librería estándar para logging. Se eliminó de inmediato.

---

## 4. Decisiones que tomé por mi cuenta (Sin consultar a la IA)

1. **Deduplicación temprana en memoria en `lectura.py`:**
   - En lugar de enviar IDs repetidos a la API o resolver colisiones en la base de datos al vuelo, decidí estructurar un diccionario en `lectura.py` que almacena el identificador único y un contador `veces_en_archivo`. Esto optimiza recursos y permite auditar duplicados antes de cualquier operación de red.

2. **Incorporación de Jitter aleatorio en el Backoff:**
   - La IA propuso un simple `time.sleep(backoff_factor * (2 ** intento))`. Decidí añadir un factor de perturbación aleatorio (`random.uniform(0.1, 0.5)`). Esto evita que múltiples clientes o reintentos concurrentes sincronicen sus peticiones sobre el servidor en el mismo milisegundo (problema de la manada atronadora).

3. **Diseño del Runbook de Guardia:**
   - Estructuré el plan de contingencia de las 3:00 a.m. pensando en un ingeniero de guardia que necesita pasos concretos de diagnóstico (comandos directos para ver logs, verificación de puertos, desbloqueo de archivos) y no teoría genérica.

