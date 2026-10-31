# Pipeline de Procesamiento de Cuentas Médicas

Pipeline ETL resiliente en Python para la ingesta, validación, consumo de API REST externa (JSONPlaceholder), persistencia de estado transaccional en SQLite y exportación a Excel.

Diseñado bajo principios de **idempotencia**, **tolerancia a fallos**, **reintentos con criterio**, **auditoría completa (logging)** y **observabilidad operativa (runbook)**.

---

## 1. ¿Qué hace el proyecto?

1. **Lectura y Normalización (`cuentas.csv`):**
   - Limpieza de cadenas (espacios, saltos de línea, comillas).
   - Detección temprana de registros no válidos (alfanuméricos como `abc`).
   - Deduplicación de identificadores, contabilizando la frecuencia de aparición de cada uno.
2. **Control de Estado e Idempotencia (`state/estado.db`):**
   - Antes de llamar a la red, verifica si el registro ya fue resuelto en ejecuciones anteriores (`OK`, `NO_EXISTE`, `INVALIDO`). Si ya está resuelto, se omite para evitar procesamiento y costos redundantes.
3. **Consumo de API con Reintentos (`api.py`):**
   - Consulta el endpoint REST con timeout explícito y backoff exponencial con jitter.
4. **Persistencia Transaccional:**
   - Actualización del estado del registro en SQLite (`UPSERT`).
5. **Exportación a Hoja de Cálculo (`output/resultado.xlsx`):**
   - Genera el reporte final de cuentas con su estado y detalle.
6. **Resumen de Ejecución y Auditoría (`logs/proceso.log`):**
   - Emite métricas consolidadas en consola y archivo rotativo.

---

## 2. Requisitos Previos e Instalación

### Requisitos de Sistema
- **Python**: 3.10 o superior (compatible con 3.11, 3.12, 3.14).
- Sistema Operativo: Windows, Linux o macOS.

### Instalación de Dependencias

1. Clonar el repositorio o ubicarse en la raíz del proyecto:
   ```bash
   cd "Reto dsinno"
   ```

2. Crear y activar el entorno virtual:
   - **En Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **En Linux/macOS:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. Instalar librerías requeridas:
   ```bash
   pip install -r requirements.txt
   ```

---

## 3. Configuración Fuera del Código

El comportamiento del sistema no tiene valores duros (*hardcoded*). Se parametriza mediante variables de entorno en el archivo [`config/.env`](file:///c:/Users/emanu/Downloads/Reto%20dsinno/config/.env), cargadas por [`config/config.py`](file:///c:/Users/emanu/Downloads/Reto%20dsinno/config/config.py):

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `url_base` | `https://jsonplaceholder.typicode.com/posts` | URL base del servicio REST |
| `timeout` | `5` | Tiempo máximo de espera por petición HTTP (en segundos) |
| `max_retries` | `3` | Número máximo de reintentos para fallos técnicos recuperables |
| `backoff_factor` | `1.0` | Factor base multiplicador para el cálculo de espera exponencial |
| `input_csv` | `cuentas.csv` | Ruta del archivo de entrada |
| `output_excel` | `output/resultado.xlsx` | Ruta del archivo Excel de salida |
| `db_state` | `state/estado.db` | Ruta de la base de datos SQLite de estado |
| `log_file` | `logs/proceso.log` | Ruta del archivo de auditoría y log |

---

## 4. Cómo se Ejecuta

Una vez configurado el archivo `.env`:

```bash
python main.py
```

Flujo de salida en consola:
- Logs en tiempo real con marca de tiempo, nivel y thread.
- Confirmación de generación del archivo Excel en `output/resultado.xlsx`.
- Tabla resumen de la corrida.

---

## 5. Manejo de Errores: Negocio vs. Técnico

El pipeline establece una separación estricta entre dos categorías de error:

```
                          ┌───────────────────────────┐
                          │   Evaluación del Registro  │
                          └─────────────┬─────────────┘
                                        │
                 ┌──────────────────────┴──────────────────────┐
                 ▼                                             ▼
       [ CASO DE NEGOCIO ]                            [ CASO TÉCNICO ]
   (Error permanente de dato)                   (Fallo transitorio de entorno)
   ───────────────────────────                   ─────────────────────────────
   • Formato no numérico ("abc")                • Caída de red / DNS failure
   • Recurso no existe (HTTP 404)                • Timeout de conexión / lectura
   • Error de cliente HTTP (400, 403)            • Errores de servidor (500, 502, 503)
                 │                                             │
                 ▼                                             ▼
        ESTADO DEFINITIVO                              REINTENTOS CON
        (NO SE REINTENTA)                            BACKOFF EXPONENCIAL
                 │                                             │
                 │                                             ├──► Si recupera ──► OK
                 │                                             └──► Si agota reintentos:
                 │                                                  ERROR_TECNICO
                 └──────────────────────┬──────────────────────┘
                                        ▼
                               Persistencia en BD
```

### 1. Casos de Negocio (Errores Semánticos / Definitivos)
- **`INVALIDO` (Formato inválido):** Identificadores como `"abc"` o vacíos. Se detectan en `lectura.py` antes de tocar la red. Reintentar contra una API una cuenta con formato inválido siempre devolverá error; por tanto, se persiste de inmediato y **no consume llamadas a la API**.
- **`NO_EXISTE` (HTTP 404 Not Found):** La cuenta no está registrada en el sistema de destino. Un recurso inexistente no aparecerá mágicamente en 2 segundos. Se marca como `NO_EXISTE` con 1 solo intento y se persiste el estado final.
- **`ERROR_CLIENTE` (HTTP 400-499 excepto 429):** Peticiones mal formadas o problemas de autenticación fijos. No se reintentan en vano.

### 2. Casos Técnicos (Errores Transitorios de Infraestructura)
- **Timeouts de conexión o lectura (`requests.exceptions.Timeout`):** Congestión momentánea en el servidor o la red.
- **Cortes de red o fallos de resolución DNS (`requests.exceptions.ConnectionError`).**
- **Errores internos del servidor remoto (`HTTP 500, 502, 503, 504` o `429 Too Many Requests`).**
- Estos fallos tienen alta probabilidad de resolverse tras una pausa, por lo que **sí son candidatos a reintento**.

---

## 6. Política de Reintentos: Dónde pusimos la frontera y por qué

> **Principio rector:** *Solo reintentar aquello que tiene probabilidad real de cambiar en el corto plazo; nunca reintentar lo que está roto por definición.*

### Frontera Decisional:

| Escenario | ¿Reintenta? | Justificación técnica |
|---|:---:|---|
| **ID no numérico** | ❌ **NO** | Error de formato en origen. La API rechazará la solicitud siempre. Reintentar gasta ancho de banda y tiempo. |
| **HTTP 404** | ❌ **NO** | Idempotencia negativa: la entidad no existe en la base de datos destino. Reintentar es spam inútil a la API. |
| **HTTP 400 / 401 / 403** | ❌ **NO** | Errores deterministas de contrato o permisos fijos. Requieren intervención humana o corrección de credenciales. |
| **HTTP 5xx (500, 502, 503, 504)** |  **SÍ** | Microservicio reiniciándose, saturación temporal o fallo momentáneo de balanceador. |
| **HTTP 429 (Rate Limit)** |  **SÍ** | Superación de cuota por segundo. El backoff le permite enfriarse a la ventana de tasa. |
| **Timeout / Connection Error** |  **SÍ** | Fluctuación de red, degradación de socket transitoria. |

### Estrategia de Espera: Backoff Exponencial con Jitter
Para evitar el problema de la "manada atronadora" (*thundering herd problem*), donde múltiples hilos o peticiones golpean el servidor al mismo instante exacto, la espera se calcula mediante:

```python
espera = (backoff_factor * (2 ** (intento - 1))) + jitter
```

- **Intento 1 fallido:** Espera ≈ 1.0 s + jitter (0.1 a 0.5 s)
- **Intento 2 fallido:** Espera ≈ 2.0 s + jitter (0.1 a 0.5 s)
- **Intento 3 fallido:** Si agota los 3 reintentos configurados, se abandona definitivamente y se califica como `ERROR_TECNICO`, registrando en la base de datos y en los logs la causa exacta del último error.

---

## 7. LA DECISIÓN QUE QUEREMOS VER: Tratamiento de Identificadores Duplicados

> **El reto planteaba:** *El CSV tiene identificadores repetidos. No te vamos a decir qué hacer con ellos. Decídelo tú y escribe en el README qué decidiste y por qué. No hay respuesta correcta: lo que evaluamos es el criterio, no la elección.*

### Nuestra Decisión
Se decidió **deduplicar en la fase de lectura temprana** consolidando cada identificador a un único registro en la base de datos y en el Excel final, pero **preservando la trazabilidad de frecuencia mediante una columna explícita (`veces_en_archivo`)**.

### Justificación y Criterio Técnico / de Negocio:

1. **Eficiencia de Red y Costo Operativo (No saturar la API):**
   - En el archivo entregado, identificadores como el `7` aparecen repetidos 3 veces y el `12` aparece 2 veces.
   - Realizar 3 peticiones HTTP idénticas para la cuenta `7` a las 3:00 a.m. desperdicia recursos, alarga la ventana de procesamiento nocturno y arriesga bloqueos.

2. **Claridad para el Equipo de Auditoría:**
   - El equipo de auditoría médica revisa el Excel en la mañana para conciliar cuentas radicadas. Presentar filas duplicadas con el mismo identificador generaría confusión operativa: ¿se auditó dos veces?, ¿se debe pagar dos veces?
   - Una única fila por cuenta médica ofrece una vista limpia, concisa y libre de ruido.

3. **Trazabilidad de Negocio sin Pérdida de Información:**
   - Descartar los duplicados "en silencio" sería un error grave de auditoría: si la clínica radicó la misma cuenta 3 veces, ese indicio puede señalar un error de facturación doble o un reintento manual erróneo por parte de la clínica.
   - Al capturar y persistir el campo `veces_en_archivo`, el equipo de auditoría puede ordenar o filtrar el Excel por esa columna y detectar anomalías en la radicación de origen sin sacrificar la idempotencia del sistema.

4. **Idempotencia y Clave Primaria:**
   - En la base de datos de estado, el campo `id` es `PRIMARY KEY`. El mecanismo de `UPSERT` actualiza la metadata sin corromper el histórico ni generar duplicados al re-ejecutar el proceso.

---

## 8. Logging y Protección de Datos

Configurado en [`logger.py`](file:///c:/Users/emanu/Downloads/Reto%20dsinno/logger.py):
- **Doble Handler:**
  - `StreamHandler`: salida a consola en tiempo real para ejecución interactiva.
  - `RotatingFileHandler`: archivo físico en `logs/proceso.log` con rotación a los **5 MB** y conservación de hasta **3 archivos históricos** (`proceso.log.1`, `proceso.log.2`, etc.) para prevenir saturación de disco.
- **Formato estándar:**
  ```text
  %(asctime)s [%(levelname)s] [ID: %(threadName)s] %(message)s
  ```
- **Protección de Datos Sensibles:** Los registros **no vuelcan payloads médicos, nombres o cuerpos completos** de respuesta (`body`, `title`, datos personales). Únicamente se auditan metadatos operativos (número de filas, estado final, tipo de fallo HTTP y tiempos).

---

## 9. Resumen de Ejecución

Al culminar la corrida, la función `imprimir_resumen()` consulta de forma independiente la base de datos SQLite para emitir el consolidado oficial:

```text
============================================================
         RESUMEN DE EJECUCIÓN
============================================================
  Filas leídas del CSV (sin cabecera) : 20
  IDs únicos registrados en BD        : 17
============================================================
  ✔  Resueltas con éxito  (OK)        : 13
============================================================
  Cuentas con fallos:
     • NO_EXISTE    (HTTP 404)         : 3
     • INVALIDO     (formato inválido) : 1
     • ERROR_TECNICO (timeout / 5xx)   : 0
     TOTAL fallidas                    : 4
============================================================
  ↷  Omitidas esta corrida (ya resueltas): 17
============================================================
```

> **Nota sobre los fallos:** Los identificadores `0`, `101` y `150` corresponden a `NO_EXISTE` porque JSONPlaceholder solo contiene registros del 1 al 100; mientras que `abc` es catalogado como `INVALIDO` previo a consultar la red.

---

## 10. Runbook Operativo (Guardia 3:00 AM)

> **Contexto:** Te llaman de guardia a las 3:00 a.m. porque el proceso automatizado falló o el reporte no llegó a tiempo. Sigue este procedimiento estándar de operación:

### Paso 1: Triage Inicial y Diagnóstico Rápido
1. Abre el archivo de logs más reciente:
   ```bash
   # En Windows PowerShell:
   Get-Content -Tail 50 -Wait logs\proceso.log

   # En Linux:
   tail -n 50 -f logs/proceso.log
   ```
2. Busca líneas con etiqueta `[ERROR]` o `[CRITICAL]`.
3. Identifica el tipo de error:
   - **Caso A (Conectividad externa):** Mensajes repetidos de `Error de conexion/timeout: ConnectTimeout` o `HTTP 503`.
   - **Caso B (Permisos o disco):** `PermissionError` o `Disk full` al escribir en `output/` o `state/`.
   - **Caso C (Formato de entrada corrupto):** Error de codificación en `cuentas.csv` (`UnicodeDecodeError`).

### Paso 2: Acciones de Mitigación Inmediatas

| Causa Raíz Detectada | Acción Inmediata de Mitigación |
|---|---|
| **API remota caída o degradada** | 1. Verificar conectividad: `curl -I https://jsonplaceholder.typicode.com/posts/1`<br>2. Si la API externa está caída, no forzar ejecuciones.<br>3. Notificar al canal de incidentes que el proveedor externo está fuera de servicio. |
| **Timeouts frecuentes por latencia alta** | En `config/.env`, incrementar temporalmente:<br>`timeout = 15`<br>`max_retries = 5`<br>Re-ejecutar `python main.py`. |
| **Archivo Excel bloqueado (`PermissionError`)** | Un usuario o proceso de auditoría dejó abierto `resultado.xlsx` en el servidor. Cerrar el proceso o archivo y volver a lanzar el script. |
| **La base de datos `estado.db` está bloqueada** | Matar cualquier proceso zombi de Python que retenga el lock de SQLite:<br>`taskkill /F /IM python.exe` (Windows)<br>`pkill -f python` (Linux) |

### Paso 3: Reanudación Segura (Idempotencia)
Gracias al diseño con persistencia de estados en SQLite:
1. **NO necesitas limpiar la base de datos ni editar el CSV.**
2. Vuelve a ejecutar directamente:
   ```bash
   python main.py
   ```
3. El proceso detectará automáticamente los registros previamente completados (`OK`, `NO_EXISTE`, `INVALIDO`), los saltará (**0 costo de llamadas repetidas**) y **solo reintentará los pendientes o aquellos con `ERROR_TECNICO`**.
4. Una vez finalizado, verifica que el archivo `output/resultado.xlsx` haya actualizado su timestamp de modificación.

