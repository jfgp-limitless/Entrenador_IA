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
        SELECT nombre, tipo, fecha, hora, descripcion,
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

    # Últimas 4 semanas detallado
    actividades = conn.execute("""
        SELECT tipo, fecha, distancia_km, tiempo_segundos, fc_media, nombre
        FROM actividades
        WHERE fecha >= date('now', '-28 days')
        ORDER BY fecha DESC
    """).fetchall()

    # Resumen 90 días
    resumen = conn.execute("""
        SELECT tipo,
               COUNT(*) as count,
               ROUND(SUM(distancia_km),1) as km,
               ROUND(SUM(tiempo_segundos)/3600.0,1) as horas
        FROM actividades
        WHERE fecha >= date('now', '-90 days')
        GROUP BY tipo
    """).fetchall()

    # Fuerza reciente
    tabla_fuerza = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workouts_fuerza'").fetchone()
    fuerza_reciente = []
    if tabla_fuerza:
        fuerza_reciente = conn.execute("""
            SELECT fecha, nombre, total_sets, volumen_kg, musculos_json
            FROM workouts_fuerza
            WHERE fecha >= date('now', '-28 days')
            ORDER BY fecha DESC
        """).fetchall()

    # Eventos próximos
    tabla_eventos = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='eventos'").fetchone()
    eventos = []
    if tabla_eventos:
        eventos = conn.execute("""
            SELECT nombre, tipo, fecha,
                   CAST(julianday(fecha) - julianday('now') AS INTEGER) as dias
            FROM eventos WHERE fecha >= date('now') ORDER BY fecha ASC LIMIT 5
        """).fetchall()

    conn.close()

    ctx = """Eres el entrenador personal de Felipe. Tienes acceso completo a su historial de entrenamiento.

PERFIL DEL ATLETA:
- Nombre: Felipe
- Peso: ~80kg, Altura: 1.83m
- Objetivo principal: Hipertrofia (60%) + Triatlón (40%)
- Disciplinas activas: Run, WeightTraining. Próximamente: Swim, Ride
- Lesión activa: Cintilla iliotibial (IT Band) — IMPORTANTE considerar siempre
- Nivel: Intermedio, lleva tiempo entrenando gym y corriendo
- No tiene base en ciclismo ni natación aún

FILOSOFÍA DE ENTRENAMIENTO:
- Priorizar recuperación de cintilla iliotibial antes de aumentar volumen de carrera
- Hipertrofia: periodización con progresión de cargas
- Triatlón: construcción gradual de base aeróbica
- Nutrición: consejos prácticos de timing, no dieta estricta

RESUMEN ÚLTIMOS 90 DÍAS:\n"""

    for r in resumen:
        ctx += f"- {r['tipo']}: {r['count']} sesiones, {r['km']}km, {r['horas']}h\n"

    ctx += "\nACTIVIDADES ÚLTIMAS 4 SEMANAS:\n"
    for a in actividades:
        tiempo_min = round((a["tiempo_segundos"] or 0) / 60)
        ctx += f"- {a['fecha']} | {a['tipo']} | {a['nombre']} | {a['distancia_km']}km | {tiempo_min}min | FC: {a['fc_media'] or 'N/A'}\n"

    if fuerza_reciente:
        ctx += "\nWORKOUTS DE FUERZA RECIENTES:\n"
        for w in fuerza_reciente:
            musculos = json.loads(w["musculos_json"])
            ctx += f"- {w['fecha']} | {w['nombre']} | {w['total_sets']} sets | {w['volumen_kg']}kg vol | Músculos: {', '.join(musculos.keys())}\n"

    if eventos:
        ctx += "\nEVENTOS PRÓXIMOS:\n"
        for e in eventos:
            ctx += f"- {e['nombre']} ({e['tipo']}) en {e['dias']} días ({e['fecha']})\n"

    ctx += "\nRESPONDE SIEMPRE EN ESPAÑOL. Sé directo, específico y considera la lesión de cintilla iliotibial en cualquier recomendación de carrera o pierna."

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

# ── Rutas Flask ───────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

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
    import requests as req
    data = request.json
    historial = data.get("historial", [])
    mensaje = data.get("mensaje", "")
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not api_key:
        return jsonify({"error": "Falta ANTHROPIC_API_KEY en .env"}), 400

    sistema = construir_contexto()
    messages = historial + [{"role": "user", "content": mensaje}]

    response = req.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "system": sistema,
            "messages": messages
        }
    )

    if response.status_code != 200:
        return jsonify({"error": response.text}), 500

    respuesta = response.json()["content"][0]["text"]
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