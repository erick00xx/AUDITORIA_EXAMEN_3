# backend/database_setup.py
import sqlite3

DB_PATH = "tickets.db"

def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ÚNICAMENTE creamos la tabla de tickets
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL,
        status TEXT NOT NULL
    )
    ''')

    conn.commit()
    conn.close()
    print("Base de datos 'tickets.db' y tabla 'tickets' configuradas correctamente.")

if __name__ == "__main__":
    setup_database()