import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "entrenador.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def crear_tablas():
    conn = get_connection()
    c = conn.cursor()

    # Actividades de Strava (runs, rides, etc)
    c.execute("""
        CREATE TABLE IF NOT EXISTS actividades (
            id INTEGER PRIMARY KEY,
            strava_id TEXT UNIQUE,
            nombre TEXT,
            tipo TEXT,
            fecha TEXT,
            distancia_km REAL,
            tiempo_segundos INTEGER,
            velocidad_media REAL,
            fc_media INTEGER,
            fc_maxima INTEGER,
            desnivel_positivo REAL,
            calorias INTEGER,
            descripcion TEXT,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Sueño y métricas de recuperación (Apple Health después)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sueno (
            id INTEGER PRIMARY KEY,
            fecha TEXT UNIQUE,
            horas_totales REAL,
            horas_profundo REAL,
            horas_rem REAL,
            horas_ligero REAL,
            hrv REAL,
            fc_reposo INTEGER,
            spo2 REAL,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Lesiones activas o pasadas
    c.execute("""
        CREATE TABLE IF NOT EXISTS lesiones (
            id INTEGER PRIMARY KEY,
            descripcion TEXT,
            zona_corporal TEXT,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            activa INTEGER DEFAULT 1,
            notas TEXT,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Eventos importantes (carreras, parciales, viajes)
    c.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY,
            nombre TEXT,
            tipo TEXT,
            fecha TEXT,
            descripcion TEXT,
            completado INTEGER DEFAULT 0,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Perfil del atleta
    c.execute("""
        CREATE TABLE IF NOT EXISTS perfil (
            id INTEGER PRIMARY KEY,
            nombre TEXT,
            edad INTEGER,
            peso_kg REAL,
            altura_cm REAL,
            objetivo_principal TEXT,
            objetivo_secundario TEXT,
            dias_entreno_semana INTEGER,
            actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS activity_streams (
            id INTEGER PRIMARY KEY,
            strava_id TEXT UNIQUE,
            time_data TEXT,
            distance_data TEXT,
            heartrate_data TEXT,
            velocity_data TEXT,
            altitude_data TEXT,
            cadence_data TEXT,
            latlng_data TEXT,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("✓ Base de datos lista en data/entrenador.db")

if __name__ == "__main__":
    crear_tablas()