import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, render_template, jsonify, request
from database import get_connection

app = Flask(__name__)

# ── Stats generales ──────────────────────────────────────────
def get_stats_generales(dias=30):
    conn = get_connection()
    c = conn.cursor()
    stats = {}
    stats["total_actividades"] = c.execute(
        "SELECT COUNT(*) FROM actividades WHERE fecha >= date('now',?)", (f'-{dias} days',)
    ).fetchone()[0]
    stats["distancia_total"] = c.execute(
        "SELECT ROUND(SUM(distancia_km),1) FROM actividades WHERE fecha >= date('now',?)", (f'-{dias} days',)
    ).fetchone()[0] or 0
    stats["tiempo_total_horas"] = round((c.execute(
        "SELECT SUM(tiempo_segundos) FROM actividades WHERE fecha >= date('now',?)", (f'-{dias} days',)
    ).fetchone()[0] or 0)/3600,1)
    stats["fc_media"] = c.execute(
        "SELECT ROUND(AVG(fc_media),0) FROM actividades WHERE fecha >= date('now',?) AND fc_media IS NOT NULL", (f'-{dias} days',)
    ).fetchone()[0] or 0

    for tipo, key in [("Run","run"),("Ride","ride"),("Swim","swim"),("WeightTraining","fuerza")]:
        stats[f"km_{key}"] = c.execute(
            "SELECT ROUND(SUM(distancia_km),1) FROM actividades WHERE tipo=? AND fecha >= date('now',?)", (tipo, f'-{dias} days')
        ).fetchone()[0] or 0
        stats[f"count_{key}"] = c.execute(
            "SELECT COUNT(*) FROM actividades WHERE tipo=? AND fecha >= date('now',?)", (tipo, f'-{dias} days')
        ).fetchone()[0] or 0
        stats[f"horas_{key}"] = round((c.execute(
            "SELECT SUM(tiempo_segundos) FROM actividades WHERE tipo=? AND fecha >= date('now',?)", (tipo, f'-{dias} days')
        ).fetchone()[0] or 0)/3600,1)

    tabla_existe = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workouts_fuerza'").fetchone()
    if tabla_existe:
        stats["volumen_total_kg"] = c.execute(
            "SELECT ROUND(SUM(volumen_kg),0) FROM workouts_fuerza WHERE fecha >= date('now',?)", (f'-{dias} days',)
        ).fetchone()[0] or 0
        stats["total_sets"] = c.execute(
            "SELECT SUM(total_sets) FROM workouts_fuerza WHERE fecha >= date('now',?)", (f'-{dias} days',)
        ).fetchone()[0] or 0
        stats["workouts_fuerza_count"] = c.execute(
            "SELECT COUNT(*) FROM workouts_fuerza WHERE fecha >= date('now',?)", (f'-{dias} days',)
        ).fetchone()[0] or 0
    else:
        stats["volumen_total_kg"] = 0
        stats["total_sets"] = 0
        stats["workouts_fuerza_count"] = 0

    conn.close()
    return stats

# ── Actividades recientes ────────────────────────────────────
def get_actividades_recientes(limite=20, tipo=None, dias=30):
    conn = get_connection()
    query = """SELECT strava_id, nombre, tipo, fecha, distancia_km, tiempo_segundos,
               velocidad_media, fc_media, fc_maxima, desnivel_positivo, calorias
               FROM actividades WHERE fecha >= date('now',?)"""
    params = [f'-{dias} days']
    if tipo and tipo != "all":
        query += " AND tipo = ?"
        params.append(tipo)
    query += " ORDER BY fecha DESC LIMIT ?"
    params.append(limite)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Distancia semanal ────────────────────────────────────────
def get_distancia_semanal(tipo=None, semanas=12):
    conn = get_connection()
    query = f"""
        SELECT strftime('%Y-W%W', fecha) as semana,
               ROUND(SUM(distancia_km), 1) as distancia,
               ROUND(SUM(tiempo_segundos)/3600.0, 1) as horas,
               COUNT(*) as actividades
        FROM actividades
        WHERE fecha >= date('now', '-{semanas} weeks')
    """
    params = []
    if tipo and tipo != "all":
        query += " AND tipo = ?"
        params.append(tipo)
    query += " GROUP BY semana ORDER BY semana ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Horas semanales ──────────────────────────────────────────
def get_horas_semanales(semanas=12):
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT strftime('%Y-W%W', fecha) as semana,
               tipo,
               ROUND(SUM(tiempo_segundos)/3600.0, 2) as horas
        FROM actividades
        WHERE fecha >= date('now', '-{semanas*7} days')
        GROUP BY semana, tipo
        ORDER BY semana ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT strftime('%Y-W%W', fecha) as semana,
               tipo,
               ROUND(SUM(tiempo_segundos)/3600.0, 2) as horas
        FROM actividades
        WHERE fecha >= date('now', '-{semanas} weeks')
        GROUP BY semana, tipo
        ORDER BY semana ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── FC histórico ─────────────────────────────────────────────
def get_fc_historico(tipo=None, dias=60):
    conn = get_connection()
    query = "SELECT fecha, fc_media, fc_maxima, tipo FROM actividades WHERE fc_media IS NOT NULL AND fecha >= date('now',?)"
    params = [f'-{dias} days']
    if tipo and tipo != "all":
        query += " AND tipo = ?"
        params.append(tipo)
    query += " ORDER BY fecha ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
    conn = get_connection()
    query = "SELECT fecha, fc_media, fc_maxima, tipo FROM actividades WHERE fc_media IS NOT NULL AND fecha >= date('now','-60 days')"
    params = []
    if tipo and tipo != "all":
        query += " AND tipo = ?"
        params.append(tipo)
    query += " ORDER BY fecha ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Fuerza: radar de músculos ────────────────────────────────
def get_radar_musculos(dias=30):
    conn = get_connection()
    tabla_existe = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workouts_fuerza'").fetchone()
    if not tabla_existe:
        conn.close()
        return {}

    rows = conn.execute(f"""
        SELECT musculos_json FROM workouts_fuerza
        WHERE fecha >= date('now', '-{dias} days')
    """).fetchall()
    conn.close()

    totales = {}
    for r in rows:
        musculos = json.loads(r["musculos_json"])
        for m, sets in musculos.items():
            totales[m] = totales.get(m, 0) + sets
    return totales

# ── Fuerza: métricas ─────────────────────────────────────────
def get_metricas_fuerza(dias=30):
    conn = get_connection()
    tabla_existe = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workouts_fuerza'").fetchone()
    if not tabla_existe:
        conn.close()
        return {}

    row = conn.execute(f"""
        SELECT COUNT(*) as workouts,
               SUM(total_sets) as sets,
               ROUND(SUM(volumen_kg),0) as volumen,
               SUM(total_reps) as reps
        FROM workouts_fuerza
        WHERE fecha >= date('now', '-{dias} days')
    """).fetchone()
    conn.close()
    return dict(row) if row else {}

# ── Fuerza: progresión ejercicio ──────────────────────────────
def get_progresion_ejercicio(ejercicio):
    conn = get_connection()
    tabla_existe = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workouts_fuerza'").fetchone()
    if not tabla_existe:
        conn.close()
        return []

    rows = conn.execute("""
        SELECT fecha, ejercicios_json FROM workouts_fuerza ORDER BY fecha ASC
    """).fetchall()
    conn.close()

    progresion = []
    for r in rows:
        ejercicios = json.loads(r["ejercicios_json"])
        for e in ejercicios:
            if ejercicio.lower() in e["nombre"].lower():
                peso_max = max((s["peso_kg"] for s in e["series"]), default=0)
                vol = sum(s["peso_kg"] * s["reps"] for s in e["series"])
                progresion.append({
                    "fecha": r["fecha"],
                    "peso_max": peso_max,
                    "volumen": round(vol, 1)
                })
    return progresion

# ── Eventos próximos ─────────────────────────────────────────
def get_eventos_proximos():
    conn = get_connection()
    tabla_existe = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='eventos'").fetchone()
    if not tabla_existe:
        conn.close()
        return []
    rows = conn.execute("""
        SELECT nombre, categoria, fecha, hora, descripcion,
               CAST(julianday(fecha) - julianday('now') AS INTEGER) as dias_restantes
        FROM eventos
        WHERE fecha >= date('now')
        ORDER BY fecha ASC
        LIMIT 10
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Contexto para Claude ─────────────────────────────────────
def construir_contexto():
    conn = get_connection()
    from datetime import date

    hoy = date.today().strftime('%Y-%m-%d')
    dia_semana = date.today().strftime('%A')

    # ── Resumen cardio 90 días ───────────────────────────────
    resumen_cardio = conn.execute("""
        SELECT tipo,
               COUNT(*) as sesiones,
               ROUND(SUM(distancia_km),1) as km,
               ROUND(SUM(tiempo_segundos)/3600.0,1) as horas,
               ROUND(AVG(fc_media),0) as fc_avg
        FROM actividades
        WHERE fecha >= date('now','-90 days')
        AND tipo != 'WeightTraining'
        GROUP BY tipo
    """).fetchall()

    # ── Actividades cardio últimas 8 semanas (una por semana resumida) ──
    actividades_cardio = conn.execute("""
        SELECT tipo, fecha, distancia_km, tiempo_segundos,
               fc_media, fc_maxima, velocidad_media, nombre
        FROM actividades
        WHERE fecha >= date('now','-56 days')
        AND tipo != 'WeightTraining'
        ORDER BY fecha DESC
    """).fetchall()

    # ── Workouts fuerza últimos 15 días con detalle ──────────
    tabla_fuerza = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='workouts_fuerza'"
    ).fetchone()

    workouts_fuerza = []
    if tabla_fuerza:
        workouts_fuerza = conn.execute("""
            SELECT fecha, nombre, total_sets, total_reps, volumen_kg,
                   musculos_json, ejercicios_json
            FROM workouts_fuerza
            WHERE fecha >= date('now','-15 days')
            ORDER BY fecha DESC
        """).fetchall()

    # ── Todos los workouts para progresión de cargas ─────────
    historial_fuerza = []
    if tabla_fuerza:
        historial_fuerza = conn.execute("""
            SELECT fecha, nombre, ejercicios_json
            FROM workouts_fuerza
            ORDER BY fecha DESC
            LIMIT 20
        """).fetchall()

    # ── Zonas HR de actividades recientes ────────────────────
    streams_recientes = conn.execute("""
        SELECT a.fecha, a.tipo, a.nombre, s.heartrate_data
        FROM actividades a
        JOIN activity_streams s ON a.strava_id = s.strava_id
        WHERE a.fecha >= date('now','-30 days')
        AND s.heartrate_data IS NOT NULL
        AND s.heartrate_data != '[]'
        ORDER BY a.fecha DESC
        LIMIT 5
    """).fetchall()

    # ── Eventos próximos ─────────────────────────────────────
    tabla_eventos = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='eventos'"
    ).fetchone()
    eventos = []
    if tabla_eventos:
        eventos = conn.execute("""
            SELECT nombre, categoria, fecha,
                   CAST(julianday(fecha) - julianday('now') AS INTEGER) as dias
            FROM eventos
            WHERE fecha >= date('now')
            ORDER BY fecha ASC
            LIMIT 8
        """).fetchall()

    # ── Calcular peso máximo por ejercicio clave ─────────────
    pesos_max = {}
    ejercicios_clave = {
        'bench press': 'Bench Press',
        'press de banca': 'Bench Press',
        'squat': 'Squat',
        'sentadilla': 'Squat',
        'deadlift': 'Deadlift',
        'peso muerto': 'Deadlift',
        'overhead press': 'OHP',
        'shoulder press': 'OHP',
        'pull up': 'Pull Up',
        'dominadas': 'Pull Up',
        'row': 'Row',
    }
    for w in historial_fuerza:
        ejercicios = json.loads(w['ejercicios_json'])
        for e in ejercicios:
            nombre_low = e['nombre'].lower()
            for key, norm in ejercicios_clave.items():
                if key in nombre_low:
                    peso = max((s['peso_kg'] for s in e['series']), default=0)
                    if norm not in pesos_max or peso > pesos_max[norm]['peso']:
                        pesos_max[norm] = {'peso': peso, 'fecha': w['fecha']}

    conn.close()

    FC_MAX = 198  # 220 - 22 años
    ZONAS = [
        ('Z1 Recovery',  FC_MAX*0.50, FC_MAX*0.60),
        ('Z2 Base',      FC_MAX*0.60, FC_MAX*0.70),
        ('Z3 Tempo',     FC_MAX*0.70, FC_MAX*0.80),
        ('Z4 Threshold', FC_MAX*0.80, FC_MAX*0.90),
        ('Z5 Max',       FC_MAX*0.90, FC_MAX),
    ]

    def calcular_zonas(hr_data_json):
        try:
            hrs = json.loads(hr_data_json)
            hrs = [h for h in hrs if h and h > 50]
            if not hrs:
                return None
            total = len(hrs)
            dist = {}
            for h in hrs:
                for nombre, mn, mx in ZONAS:
                    if mn <= h < mx:
                        dist[nombre] = dist.get(nombre, 0) + 1
                        break
            return {k: round(v/total*100) for k, v in dist.items()}
        except:
            return None

    def pace_str(dist_km, tiempo_seg):
        if not dist_km or not tiempo_seg or dist_km == 0:
            return None
        sec_km = tiempo_seg / dist_km
        return f"{int(sec_km//60)}:{int(sec_km%60):02d}/km"

    # ── CONSTRUIR EL SYSTEM PROMPT ───────────────────────────
    ctx = f"""Eres Coach Aria, entrenadora personal de Felipe. Tienes acceso completo a su historial de entrenamiento actualizado en tiempo real.

INSTRUCCIONES DE COMPORTAMIENTO:
- Responde SIEMPRE en español, tono directo, motivador y honesto
- Sé específico: cuando recomiendes ejercicios incluye series, reps y peso sugerido basado en su historial
- SIEMPRE considera la cintilla iliotibial (IT band) en cualquier recomendación de carrera o ejercicio de pierna — es la lesión activa más importante
- Para hipertrofia: prioriza progresión de cargas, volumen por grupo muscular, descanso adecuado
- Para triatlón: construcción gradual de base aeróbica sin interferir con recuperación muscular
- Nutrición: consejos prácticos de timing pre/post entreno, no dietas estrictas
- Si hay eventos o parciales próximos, ajusta la carga de entrenamiento automáticamente
- Cuando no tienes datos suficientes, dilo claramente y pide más información
- Hoy es {dia_semana} {hoy}

PERFIL DEL ATLETA:
- Nombre: Felipe | Edad: 22 años | Peso: ~80kg | Altura: 1.83m
- Objetivo principal: Hipertrofia 60% + Triatlón 40%
- Split objetivo: 60% gym (hipertrofia) + 40% cardio (run/swim/bike)
- Disciplinas activas: Run, WeightTraining
- Por iniciar: Swim y Ride — SIN BASE en ninguna de las dos
- Lesión ACTIVA: Cintilla iliotibial (IT band syndrome)
  → Considerar SIEMPRE en ejercicios de pierna y carrera
  → Evitar: bajadas largas, cambios de ritmo bruscos, volumen alto de carrera
  → Incluir: trabajo de glúteos, foam roller, estiramientos específicos
- Nivel: Intermedio — lleva tiempo en gym y running, promedio en ambas

PESOS MÁXIMOS HISTÓRICOS:
"""
    if pesos_max:
        for ejercicio, data in pesos_max.items():
            ctx += f"  {ejercicio}: {data['peso']}kg (último récord: {data['fecha']})\n"
    else:
        ctx += "  Sin datos suficientes aún\n"

    ctx += "\nRESUMEN CARDIO ÚLTIMOS 90 DÍAS:\n"
    if resumen_cardio:
        for r in resumen_cardio:
            ctx += f"  {r['tipo']}: {r['sesiones']} sesiones | {r['km']}km | {r['horas']}h | FC avg {r['fc_avg'] or 'N/A'} bpm\n"
    else:
        ctx += "  Sin actividades cardio en este periodo\n"

    ctx += "\nACTIVIDADES CARDIO RECIENTES (últimas 8 semanas):\n"
    for a in actividades_cardio:
        pace = pace_str(a['distancia_km'], a['tiempo_segundos'])
        tiempo_min = round((a['tiempo_segundos'] or 0) / 60)
        ctx += f"  {a['fecha']} | {a['tipo']} | {a['distancia_km']}km | {tiempo_min}min"
        if pace:
            ctx += f" | pace {pace}"
        if a['fc_media']:
            ctx += f" | FC {a['fc_media']}avg/{a['fc_maxima']}max"
        ctx += "\n"

    if streams_recientes:
        ctx += "\nZONAS HR ACTIVIDADES RECIENTES:\n"
        for s in streams_recientes:
            zonas = calcular_zonas(s['heartrate_data'])
            if zonas:
                zonas_str = " | ".join([f"{k}: {v}%" for k, v in sorted(zonas.items())])
                ctx += f"  {s['fecha']} {s['nombre']}: {zonas_str}\n"

    if workouts_fuerza:
        ctx += "\nWORKOUTS DE FUERZA ÚLTIMOS 15 DÍAS (con detalle completo):\n"
        for w in workouts_fuerza:
            musculos = json.loads(w['musculos_json'])
            ejercicios = json.loads(w['ejercicios_json'])
            ctx += f"\n  {w['fecha']} — {w['nombre']}\n"
            ctx += f"  Resumen: {w['total_sets']} sets | {w['total_reps']} reps | {w['volumen_kg']}kg volumen\n"
            ctx += f"  Grupos: {', '.join(musculos.keys())}\n"
            ctx += "  Ejercicios:\n"
            for e in ejercicios:
                series_str = " | ".join([f"{s['peso_kg']}kg×{s['reps']}" for s in e['series']])
                peso_max = max((s['peso_kg'] for s in e['series']), default=0)
                ctx += f"    {e['nombre']}: {series_str} → max {peso_max}kg\n"
    else:
        ctx += "\nWORKOUTS DE FUERZA: Sin sesiones en los últimos 15 días\n"

    if eventos:
        ctx += "\nEVENTOS Y CONTEXTO PRÓXIMO:\n"
        for e in eventos:
            ctx += f"  {e['nombre']} ({e['categoria']}) → en {e['dias']} días ({e['fecha']})\n"
            if e['categoria'] in ['parcial', 'examen'] and e['dias'] <= 14:
                ctx += f"    → ALERTA: semana de {e['categoria']} próxima, reducir carga de entrenamiento\n"
            if e['categoria'] == 'competencia' and e['dias'] <= 21:
                ctx += f"    → ALERTA: competencia en {e['dias']} días, entrar en fase de tapering\n"
    else:
        ctx += "\nEVENTOS: Sin eventos próximos registrados\n"

    ctx += f"\nFecha actual: {hoy} ({dia_semana})"

    return ctx

# distancia diaria
def get_distancia_diaria(tipo=None, dias=30):
    conn = get_connection()
    query = f"""
        SELECT fecha,
               ROUND(SUM(distancia_km), 2) as distancia,
               tipo
        FROM actividades
        WHERE fecha >= date('now', '-{dias} days')
    """
    params = []
    if tipo and tipo != "all":
        query += " AND tipo = ?"
        params.append(tipo)
    query += " GROUP BY fecha ORDER BY fecha ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

#funcion progreso fuerza
def get_progresion_ejercicios(dias=365):
    conn = get_connection()
    tabla = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workouts_fuerza'").fetchone()
    if not tabla:
        conn.close()
        return {}

    if dias >= 3650:
        rows = conn.execute(
            "SELECT fecha, ejercicios_json FROM workouts_fuerza ORDER BY fecha ASC"
        ).fetchall()
    else:
        rows = conn.execute(f"""
            SELECT fecha, ejercicios_json FROM workouts_fuerza
            WHERE fecha >= date('now', '-{dias} days')
            ORDER BY fecha ASC
        """).fetchall()


    # Ejercicios prioritarios en orden
    prioritarios = [
        "bench press", "press de banca", "chest press",
        "squat", "sentadilla",
        "deadlift", "peso muerto",
        "overhead press", "shoulder press",
        "row", "remo",
        "pull up", "dominadas"
    ]

    # Agrupar por ejercicio normalizado
    ejercicios_data = {}
    alias = {
        "bench press": "Bench Press", "press de banca": "Bench Press", "chest press": "Bench Press",
        "chest fly": "Chest Fly", "pec deck": "Chest Fly",
        "squat (smith machine)": "Squat", "smith machine squat": "Squat", "sentadilla": "Squat",
        "deadlift": "Deadlift", "peso muerto": "Deadlift",
        "overhead press": "Overhead Press", "shoulder press": "Overhead Press",
        "row": "Row", "remo": "Row",
        "pull up": "Pull Up", "dominadas": "Pull Up",
        "lat pulldown": "Lat Pulldown",
        "bicep curl": "Bicep Curl", "cable curl": "Bicep Curl"
    }
    for r in rows:
        ejercicios = json.loads(r["ejercicios_json"])
        for e in ejercicios:
            nombre = e["nombre"].lower()
            nombre_norm = None
            for key, norm in sorted(alias.items(), key=lambda x: -len(x[0])):
                if key in nombre:
                    nombre_norm = norm
                    break
            if not nombre_norm:
                nombre_norm = e["nombre"]

            peso_max = max((s["peso_kg"] for s in e["series"]), default=0)
            if peso_max == 0:
                continue

            if nombre_norm not in ejercicios_data:
                ejercicios_data[nombre_norm] = []

            # Evitar duplicar misma fecha
            fechas_existentes = [x["fecha"] for x in ejercicios_data[nombre_norm]]
            if r["fecha"] not in fechas_existentes:
                ejercicios_data[nombre_norm].append({
                    "fecha": r["fecha"],
                    "peso_max": peso_max
                })
            else:
                # Actualizar si hay mayor peso ese dia
                for item in ejercicios_data[nombre_norm]:
                    if item["fecha"] == r["fecha"] and peso_max > item["peso_max"]:
                        item["peso_max"] = peso_max

    # Ordenar cada ejercicio por fecha
    for key in ejercicios_data:
        ejercicios_data[key].sort(key=lambda x: x["fecha"])

    return ejercicios_data

# ── Rutas Flask ───────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/progresion_ejercicios")
def api_progresion_ejercicios():
    dias = int(request.args.get("dias", 365))
    return jsonify(get_progresion_ejercicios(dias))

@app.route("/agente")
def agente():
    return render_template("agente.html")

@app.route("/api/distancia_diaria")
def api_distancia_diaria():
    tipo = request.args.get("tipo", "all")
    dias = int(request.args.get("dias", 30))
    return jsonify(get_distancia_diaria(tipo=tipo, dias=dias))

@app.route("/api/stats")
def api_stats():
    dias = int(request.args.get("dias", 30))
    return jsonify(get_stats_generales(dias))

@app.route("/api/actividades_recientes")
def api_actividades_recientes():
    tipo = request.args.get("tipo", "all")
    dias = int(request.args.get("dias", 30))
    return jsonify(get_actividades_recientes(tipo=tipo, dias=dias))


@app.route("/api/distancia_semanal")
def api_distancia_semanal():
    tipo = request.args.get("tipo", "all")
    return jsonify(get_distancia_semanal(tipo=tipo))

@app.route("/api/horas_semanales")
def api_horas_semanales():
    semanas = int(request.args.get("semanas", 12))
    return jsonify(get_horas_semanales(semanas))

@app.route("/api/fc_historico")
def api_fc_historico():
    tipo = request.args.get("tipo", "all")
    dias = int(request.args.get("dias", 60))
    return jsonify(get_fc_historico(tipo=tipo, dias=dias))

@app.route("/api/radar_musculos")
def api_radar_musculos():
    dias = int(request.args.get("dias", 30))
    return jsonify(get_radar_musculos(dias=dias))

@app.route("/api/radar_upper")
def api_radar_upper():
    dias = int(request.args.get("dias", 3650))
    conn = get_connection()
    tabla = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workouts_fuerza'").fetchone()
    if not tabla:
        conn.close()
        return jsonify({})
    rows = conn.execute(f"""
        SELECT musculos_json FROM workouts_fuerza
        WHERE fecha >= date('now', '-{dias} days')
    """).fetchall()
    conn.close()
    grupos = {"chest":0,"back":0,"biceps":0,"triceps":0,"shoulders":0}
    for r in rows:
        for m, sets in json.loads(r["musculos_json"]).items():
            if m in grupos:
                grupos[m] += sets
    return jsonify(grupos)

@app.route("/api/radar_lower")
def api_radar_lower():
    dias = int(request.args.get("dias", 3650))
    conn = get_connection()
    tabla = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workouts_fuerza'").fetchone()
    if not tabla:
        conn.close()
        return jsonify({})
    rows = conn.execute(f"""
        SELECT musculos_json FROM workouts_fuerza
        WHERE fecha >= date('now', '-{dias} days')
    """).fetchall()
    conn.close()
    grupos = {"quads":0,"hamstrings":0,"glutes":0,"calves":0,"core":0}
    for r in rows:
        for m, sets in json.loads(r["musculos_json"]).items():
            if m in grupos:
                grupos[m] += sets
    return jsonify(grupos)

@app.route("/api/metricas_fuerza")
def api_metricas_fuerza():
    dias = int(request.args.get("dias", 30))
    return jsonify(get_metricas_fuerza(dias=dias))

@app.route("/api/eventos")
def api_eventos():
    return jsonify(get_eventos_proximos())

@app.route("/actividad/<strava_id>")
def actividad_detalle(strava_id):
    return render_template("actividad.html", strava_id=strava_id)

@app.route("/api/actividad/<strava_id>")
def api_actividad(strava_id):
    conn = get_connection()
    tipo = conn.execute(
        "SELECT tipo FROM actividades WHERE strava_id = ?", (strava_id,)
    ).fetchone()
    conn.close()
    if not tipo:
        return jsonify({"error": "Not found"}), 404
    if tipo["tipo"] == "WeightTraining":
        return jsonify(get_detalle_fuerza(strava_id))
    return jsonify(get_detalle_actividad(strava_id))


@app.route("/api/chat", methods=["POST"])
def api_chat():
    import anthropic as ant
    data = request.json
    historial = data.get("historial", [])
    mensaje = data.get("mensaje", "")
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not api_key:
        return jsonify({"error": "Falta ANTHROPIC_API_KEY en .env"}), 400

    sistema = construir_contexto()
    messages = historial + [{"role": "user", "content": mensaje}]

    client = ant.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=[
            {
                "type": "text",
                "text": sistema,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=messages
    )

    respuesta = response.content[0].text
    
    # Log de uso para monitorear caching
    uso = response.usage
    print(f"Tokens — input: {uso.input_tokens} | output: {uso.output_tokens} | cache_created: {getattr(uso, 'cache_creation_input_tokens', 0)} | cache_read: {getattr(uso, 'cache_read_input_tokens', 0)}")

    return jsonify({"respuesta": respuesta})


def get_detalle_actividad(strava_id):
    conn = get_connection()
    act = conn.execute("SELECT * FROM actividades WHERE strava_id = ?", (strava_id,)).fetchone()
    if not act:
        conn.close()
        return None

    streams = conn.execute("SELECT * FROM activity_streams WHERE strava_id = ?", (strava_id,)).fetchone()
    conn.close()

    result = dict(act)

    if streams:
        time_data = json.loads(streams["time_data"] or "[]")
        dist_data = json.loads(streams["distance_data"] or "[]")
        hr_data = json.loads(streams["heartrate_data"] or "[]")
        vel_data = json.loads(streams["velocity_data"] or "[]")
        alt_data = json.loads(streams["altitude_data"] or "[]")
        cad_data = json.loads(streams["cadence_data"] or "[]")

        has_distance = len(dist_data) > 0

        # Calcular splits por km solo si hay distancia
        splits = []
        if has_distance and time_data:
            km_actual = 1
            idx_inicio = 0
            dist_inicio = dist_data[0]

            for i, dist in enumerate(dist_data):
                km_recorrido = (dist - dist_inicio) / 1000
                if km_recorrido >= km_actual:
                    tiempo_km = time_data[i] - time_data[idx_inicio]
                    if tiempo_km > 0:
                        pace_min = int(tiempo_km // 60)
                        pace_sec = int(tiempo_km % 60)
                        fc_tramo = hr_data[idx_inicio:i+1] if hr_data else []
                        vel_tramo = vel_data[idx_inicio:i+1] if vel_data else []
                        splits.append({
                            "km": km_actual,
                            "pace_str": f"{pace_min}:{pace_sec:02d}",
                            "pace_seg": tiempo_km,
                            "fc_media": round(sum(fc_tramo)/len(fc_tramo)) if fc_tramo else None,
                            "vel_media": round(sum(vel_tramo)/len(vel_tramo)*3.6, 1) if vel_tramo else None,
                        })
                    km_actual += 1
                    idx_inicio = i

        def reducir(arr, max_pts=500):
            if not arr or len(arr) <= max_pts:
                return arr
            step = max(1, len(arr) // max_pts)
            return arr[::step]

        # Eje X: distancia si existe, sino tiempo en minutos
        if has_distance:
            eje_x = [round(d/1000, 2) for d in reducir(dist_data)]
            eje_x_label = "km"
        else:
            eje_x = [round(t/60, 1) for t in reducir(time_data)]
            eje_x_label = "min"

        # Pace desde velocity
        vel_reducida = reducir(vel_data)
        pace_stream = []
        for v in vel_reducida:
            if v and v > 0.5:
                pace_stream.append(round((1000/v)/60, 2))
            else:
                pace_stream.append(None)

        # Reducir los demas streams al mismo tamaño que eje_x
        n = len(eje_x)
        def reducir_a_n(arr):
            if not arr:
                return []
            if len(arr) <= n:
                return arr
            step = max(1, len(arr) // n)
            return arr[::step][:n]

        result["streams"] = {
            "eje_x": eje_x,
            "eje_x_label": eje_x_label,
            "heartrate": reducir_a_n(hr_data),
            "pace": pace_stream[:n] if pace_stream else [],
            "altitude": reducir_a_n(alt_data),
            "cadence": reducir_a_n(cad_data),
            "velocity": [round(v*3.6,1) for v in reducir_a_n(vel_data)]
        }
        result["splits"] = splits
        result["has_distance"] = has_distance

        result["is_indoor"] = act["nombre"] and "indoor" in act["nombre"].lower() or act["tipo"] in ["VirtualRun","VirtualRide","Workout"]
    return result

def get_detalle_fuerza(strava_id):
    conn = get_connection()
    act = conn.execute(
        "SELECT * FROM actividades WHERE strava_id = ?", (strava_id,)
    ).fetchone()

    tabla = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='workouts_fuerza'"
    ).fetchone()

    workout = None
    if tabla:
        workout = conn.execute(
            "SELECT * FROM workouts_fuerza WHERE strava_id = ?", (strava_id,)
        ).fetchone()
    conn.close()

    if not act:
        return None

    result = dict(act)
    if workout:
        result["workout"] = {
            "total_sets": workout["total_sets"],
            "total_reps": workout["total_reps"],
            "volumen_kg": workout["volumen_kg"],
            "musculos": json.loads(workout["musculos_json"]),
            "ejercicios": json.loads(workout["ejercicios_json"])
        }
    return result


if __name__ == "__main__":
    print("Dashboard corriendo en http://localhost:5000")
    app.run(debug=True, port=5000)