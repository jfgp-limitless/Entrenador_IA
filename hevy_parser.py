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
    "heel taps": "core",
    "v-up": "core",
    "plank": "core",
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

# Líneas que Hevy agrega automáticamente al final de la descripción
# y que NO representan un ejercicio (firma de la app, etc.)
LINEAS_IGNORAR = (
    "logged with hevyapp.com",
    "completed with hevyapp.com",
    "hevyapp.com",
)

def es_linea_ignorable(linea):
    linea_low = linea.lower().strip(" .")
    return any(ignorar in linea_low for ignorar in LINEAS_IGNORAR)

# Ejercicios isométricos: Hevy los registra como "X reps" en el texto,
# pero en realidad esos números son segundos sostenidos, no repeticiones.
EJERCICIOS_ISOMETRICOS = (
    "plank",
    "wall sit",
    "hollow hold",
    "side plank",
    "dead hang",
    "l-sit",
    "l sit",
    "superman hold",
)

def es_ejercicio_isometrico(nombre_ejercicio):
    if not nombre_ejercicio:
        return False
    nombre_low = nombre_ejercicio.lower()
    return any(e in nombre_low for e in EJERCICIOS_ISOMETRICOS)

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

        # Firma de Hevy ("Logged with hevyapp.com") u otras líneas de relleno:
        # se ignoran por completo, no son un ejercicio ni una serie.
        if es_linea_ignorable(linea):
            continue

        # Serie con peso: "Set N: X kg x Y" o "X lbs x Y"
        match_set = re.match(
            r"Set\s+\d+:\s+([\d.]+)\s*(kg|lbs)\s*x\s*(\d+)", linea, re.IGNORECASE
        )
        # Serie solo reps (bodyweight): "Set N: Y reps"
        match_reps = re.match(
            r"Set\s+\d+:\s+(\d+)\s*reps?$", linea, re.IGNORECASE
        )
        # Serie en tiempo (plank, etc): "Set N: Xs" o "Set N: Xmin Ys"
        match_tiempo = re.match(
            r"Set\s+\d+:\s+(?:(\d+)min\s*)?(\d+)s$", linea, re.IGNORECASE
        )
        # Warm up set (tiempo, se ignora)
        match_warmup = re.match(r"Set\s+\d+:\s+[\d]+min", linea, re.IGNORECASE)

        if match_set:
            peso_raw = float(match_set.group(1))
            unidad = match_set.group(2).lower()
            reps = int(match_set.group(3))
            peso_kg = lbs_a_kg(peso_raw) if unidad == "lbs" else peso_raw
            series_actuales.append({"peso_kg": peso_kg, "reps": reps})

        elif match_reps:
            reps = int(match_reps.group(1))
            # Si el ejercicio actual es isométrico (plank, wall sit, etc.),
            # el número que Hevy llama "reps" en realidad son segundos.
            if es_ejercicio_isometrico(ejercicio_actual):
                series_actuales.append({"peso_kg": 0, "reps": reps, "es_tiempo": True})
            else:
                series_actuales.append({"peso_kg": 0, "reps": reps})

        elif match_tiempo:
            minutos = int(match_tiempo.group(1)) if match_tiempo.group(1) else 0
            segundos = int(match_tiempo.group(2))
            total_seg = minutos * 60 + segundos
            # Para ejercicios isométricos guardamos segundos como "reps"
            series_actuales.append({"peso_kg": 0, "reps": total_seg, "es_tiempo": True})

        elif match_warmup:
            continue

        elif not linea.startswith("Set") and not linea.startswith("Warm"):
            if ejercicio_actual and series_actuales:
                ejercicios.append({
                    "nombre": ejercicio_actual,
                    "musculo": detectar_musculo(ejercicio_actual),
                    "series": series_actuales
                })
            ejercicio_actual = linea
            series_actuales = []

    if ejercicio_actual and series_actuales:
        ejercicios.append({
            "nombre": ejercicio_actual,
            "musculo": detectar_musculo(ejercicio_actual),
            "series": series_actuales
        })

    return ejercicios

def calcular_metricas_workout(ejercicios):
    total_sets = sum(len(e["series"]) for e in ejercicios)
    # Las series marcadas como "es_tiempo" (plank, wall sit...) no son repeticiones,
    # así que no deben sumarse al total de reps.
    total_reps = sum(
        s["reps"] for e in ejercicios for s in e["series"] if not s.get("es_tiempo")
    )
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