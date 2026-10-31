import sqlite3
import config.config

def inicializar_bd():
    """Crea la tabla de cuentas si no existe."""
    conn = sqlite3.connect(config.PATH_DB_STATE)
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

