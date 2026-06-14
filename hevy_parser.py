import re
from database import get_connection

# Mapeo de músculos por ejercicio
MUSCLE_MAP = {
    # CHEST
    "bench press": "chest",
    "chest press": "chest",
    "chest fly": "chest",
    "incline bench": "chest",
    "decline bench": "chest",
    "pec deck": "chest",
    "push up": "chest",
    "dip": "chest",

    # BACK
    "lat pulldown": "back",
    "seated cable row": "back",
    "t bar row": "back",
    "cable row": "back",
    "bent over row": "back",
    "pull up": "back",
    "chin up": "back",
    "rope straight arm": "back",
    "straight arm pulldown": "back",
    "shrug": "back",
    "face pull": "shoulders",

    # SHOULDERS
    "shoulder press": "shoulders",
    "overhead press": "shoulders",
    "lateral raise": "shoulders",
    "front raise": "shoulders",
    "arnold": "shoulders",
    "rear delt": "shoulders",
    "reverse fly": "shoulders",

    # BICEPS
    "bicep curl": "biceps",
    "hammer curl": "biceps",
    "preacher curl": "biceps",
    "incline curl": "biceps",
    "seated incline curl": "biceps",
    "cable curl": "biceps",
    "barbell curl": "biceps",

    # TRICEPS
    "tricep": "triceps",
    "triceps": "triceps",
    "skull crusher": "triceps",
    "pushdown": "triceps",
    "overhead tricep": "triceps",
    "close grip bench": "triceps",

    # QUADS
    "squat": "quads",
    "leg press": "quads",
    "leg extension": "quads",
    "bulgarian split squat": "quads",
    "split squat": "quads",
    "lunge": "quads",
    "hack squat": "quads",
    "step up": "quads",

    # HAMSTRINGS
    "deadlift": "hamstrings",
    "romanian deadlift": "hamstrings",
    "rdl": "hamstrings",
    "leg curl": "hamstrings",
    "lying leg curl": "hamstrings",
    "seated leg curl": "hamstrings",
    "nordic": "hamstrings",
    "good morning": "hamstrings",

    # GLUTES
    "hip thrust": "glutes",
    "hip abduction": "glutes",
    "hip adduction": "glutes",
    "glute bridge": "glutes",
    "cable kickback": "glutes",
    "donkey kick": "glutes",

    # CALVES
    "calf raise": "calves",
    "seated calf": "calves",
    "standing calf": "calves",

    # CORE
    "plank": "core",
    "crunch": "core",
    "sit up": "core",
    "ab ": "core",
    "russian twist": "core",
    "leg raise": "core",
    "cable crunch": "core",
    "hanging": "core",
}

# Grupos para los radares
UPPER_GROUPS = ["chest", "back", "biceps", "triceps", "shoulders"]
LOWER_GROUPS = ["quads", "hamstrings", "glutes", "calves", "core"]

UPPER_LABELS = {
    "chest": "Chest",
    "back": "Back",
    "biceps": "Biceps",
    "triceps": "Triceps",
    "shoulders": "Shoulders"
}

LOWER_LABELS = {
    "quads": "Quads",
    "hamstrings": "Hamstrings",
    "glutes": "Glutes",
    "calves": "Calves",
    "core": "Core"
}

def detectar_musculo(nombre_ejercicio):
    nombre = nombre_ejercicio.lower()
    # Buscar match más específico primero (más largo)
    matches = [(k, v) for k, v in MUSCLE_MAP.items() if k in nombre]
    if matches:
        # Tomar el match más largo (más específico)
        return max(matches, key=lambda x: len(x[0]))[1]
    return "other"

def lbs_a_kg(valor):
    return round(valor * 0.453592, 1)

def parsear_descripcion_hevy(descripcion):
    """
    Parsea la descripción de un workout de Hevy exportado a Strava.
    Retorna lista de ejercicios con sus series.
    """
    if not descripcion:
        return []

    ejercicios = []
    ejercicio_actual = None
    series_actuales = []

    lineas = descripcion.strip().split("\n")

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        # Detectar línea de serie: "Set N: X kg x Y" o "Set N: X lbs x Y"
        match_set = re.match(
            r"Set\s+\d+:\s+([\d.]+)\s*(kg|lbs)\s*x\s*(\d+)", linea, re.IGNORECASE
        )
        # Warm up set
        match_warmup = re.match(r"Set\s+\d+:\s+[\d]+min", linea, re.IGNORECASE)

        if match_set:
            peso_raw = float(match_set.group(1))
            unidad = match_set.group(2).lower()
            reps = int(match_set.group(3))
            peso_kg = lbs_a_kg(peso_raw) if unidad == "lbs" else peso_raw
            series_actuales.append({"peso_kg": peso_kg, "reps": reps})

        elif match_warmup:
            continue  # ignorar warm up time

        elif not linea.startswith("Set") and not linea.startswith("Warm"):
            # Es el nombre de un ejercicio nuevo
            if ejercicio_actual and series_actuales:
                ejercicios.append({
                    "nombre": ejercicio_actual,
                    "musculo": detectar_musculo(ejercicio_actual),
                    "series": series_actuales
                })
            ejercicio_actual = linea
            series_actuales = []

    # Guardar último ejercicio
    if ejercicio_actual and series_actuales:
        ejercicios.append({
            "nombre": ejercicio_actual,
            "musculo": detectar_musculo(ejercicio_actual),
            "series": series_actuales
        })

    return ejercicios

def calcular_metricas_workout(ejercicios):
    total_sets = sum(len(e["series"]) for e in ejercicios)
    total_reps = sum(s["reps"] for e in ejercicios for s in e["series"])
    volumen_total = sum(
        s["peso_kg"] * s["reps"] for e in ejercicios for s in e["series"]
    )
    musculos = {}
    for e in ejercicios:
        m = e["musculo"]
        sets_ejercicio = len(e["series"])
        musculos[m] = musculos.get(m, 0) + sets_ejercicio

    return {
        "total_sets": total_sets,
        "total_reps": total_reps,
        "volumen_kg": round(volumen_total, 1),
        "musculos": musculos
    }

def guardar_workout_fuerza(strava_id, fecha, nombre, descripcion):
    ejercicios = parsear_descripcion_hevy(descripcion)
    if not ejercicios:
        return False

    metricas = calcular_metricas_workout(ejercicios)
    conn = get_connection()
    c = conn.cursor()

    import json

    # Crear tabla si no existe
    c.execute("""
        CREATE TABLE IF NOT EXISTS workouts_fuerza (
            id INTEGER PRIMARY KEY,
            strava_id TEXT UNIQUE,
            fecha TEXT,
            nombre TEXT,
            total_sets INTEGER,
            total_reps INTEGER,
            volumen_kg REAL,
            musculos_json TEXT,
            ejercicios_json TEXT,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    existe = c.execute(
        "SELECT id FROM workouts_fuerza WHERE strava_id = ?", (strava_id,)
    ).fetchone()

    if not existe:
        c.execute("""
            INSERT INTO workouts_fuerza
            (strava_id, fecha, nombre, total_sets, total_reps, volumen_kg, musculos_json, ejercicios_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            strava_id, fecha, nombre,
            metricas["total_sets"], metricas["total_reps"], metricas["volumen_kg"],
            json.dumps(metricas["musculos"]),
            json.dumps(ejercicios)
        ))
        conn.commit()

    conn.close()
    return True

def procesar_todos_los_workouts():
    """Recorre todas las actividades WeightTraining en la DB y parsea las de Hevy."""
    conn = get_connection()
    c = conn.cursor()

    actividades = c.execute("""
        SELECT strava_id, fecha, nombre, descripcion
        FROM actividades
        WHERE tipo = 'WeightTraining'
        AND descripcion IS NOT NULL
        AND descripcion != ''
    """).fetchall()
    conn.close()

    procesados = 0
    for a in actividades:
        ok = guardar_workout_fuerza(a["strava_id"], a["fecha"], a["nombre"], a["descripcion"])
        if ok:
            procesados += 1

    print(f"✓ Workouts de fuerza procesados: {procesados} de {len(actividades)}")
    return procesados

if __name__ == "__main__":
    procesar_todos_los_workouts()