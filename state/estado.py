import sqlite3

def inicializar_bd(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cuentas (
            id TEXT PRIMARY KEY,
            estado TEXT,         -- OK, NO_EXISTE, ERROR_TECNICO, INVALIDO
            causa TEXT,
            intentos INTEGER,
            veces_en_archivo INTEGER,
            title TEXT,
            userId TEXT,
            body TEXT,
            actualizado_en DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()