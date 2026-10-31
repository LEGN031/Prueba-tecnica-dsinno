import sqlite3
from config.config import PATH_DB_STATE

def inicializar_bd():
    conn = sqlite3.connect(PATH_DB_STATE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cuentas (
            id TEXT PRIMARY KEY,
            estado TEXT NOT NULL,         -- OK, NO_EXISTE, ERROR_TECNICO, INVALIDO
            causa TEXT NOT NULL,
            intentos INTEGER DEFAULT 0,
            veces_en_archivo INTEGER DEFAULT 1,
            title TEXT,
            userId TEXT,
            body TEXT,
            actualizado_en DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def obtener_cuenta(id_cuenta):
    conn = sqlite3.connect(PATH_DB_STATE)
    cursor = conn.cursor()
    cursor.execute("SELECT estado FROM cuentas WHERE id = ?", (id_cuenta,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def guardar_resultado(id_cuenta, res, veces_en_archivo):
    conn = sqlite3.connect(PATH_DB_STATE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO cuentas (id, estado, causa, intentos, veces_en_archivo, title, userId, body, actualizado_en)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            estado = excluded.estado,
            causa = excluded.causa,
            intentos = excluded.intentos,
            veces_en_archivo = excluded.veces_en_archivo,
            title = excluded.title,
            userId = excluded.userId,
            body = excluded.body,
            actualizado_en = CURRENT_TIMESTAMP
    ''', (
        id_cuenta,
        res["estado"],
        res["causa"],
        res["intentos"],
        veces_en_archivo,
        res.get("title"),
        res.get("userId"),
        res.get("body")
    ))
    conn.commit()
    conn.close()