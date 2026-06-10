import os
import json
import time
import requests
from dotenv import load_dotenv
from database import get_connection

load_dotenv()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")

def obtener_access_token():
    response = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    })
    return response.json()["access_token"]

def obtener_streams(access_token, strava_id):
    headers = {"Authorization": f"Bearer {access_token}"}
    keys = "time,distance,heartrate,velocity_smooth,altitude,cadence,latlng"
    response = requests.get(
        f"https://www.strava.com/api/v3/activities/{strava_id}/streams",
        headers=headers,
        params={"keys": keys, "key_by_type": "true", "resolution": "high"}
    )
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 429:
        print("  Rate limit alcanzado, esperando 60s...")
        time.sleep(60)
        return obtener_streams(access_token, strava_id)
    return None

def calcular_splits_km(time_data, distance_data, heartrate_data=None):
    """Calcula pace, FC media y desnivel por cada km."""
    if not time_data or not distance_data:
        return []

    splits = []
    km_actual = 1
    idx_inicio = 0
    dist_inicio = distance_data[0]

    for i, dist in enumerate(distance_data):
        distancia_recorrida = (dist - dist_inicio) / 1000  # en km
        if distancia_recorrida >= km_actual:
            tiempo_km = time_data[i] - time_data[idx_inicio]
            if tiempo_km > 0:
                pace_seg = tiempo_km  # segundos por km
                pace_min = int(pace_seg // 60)
                pace_sec = int(pace_seg % 60)

                fc_media = None
                if heartrate_data and len(heartrate_data) > i:
                    fc_tramo = heartrate_data[idx_inicio:i+1]
                    fc_media = round(sum(fc_tramo) / len(fc_tramo)) if fc_tramo else None

                splits.append({
                    "km": km_actual,
                    "pace_segundos": tiempo_km,
                    "pace_str": f"{pace_min}:{pace_sec:02d}",
                    "fc_media": fc_media
                })

            km_actual += 1
            idx_inicio = i

    return splits

def sincronizar_streams():
    conn = get_connection()

    # Solo actividades que NO son WeightTraining y no tienen streams aun
    actividades = conn.execute("""
        SELECT a.strava_id, a.tipo, a.nombre
        FROM actividades a
        LEFT JOIN activity_streams s ON a.strava_id = s.strava_id
        WHERE a.tipo != 'WeightTraining'
        AND s.strava_id IS NULL
    """).fetchall()
    conn.close()

    if not actividades:
        print("Todos los streams ya estan sincronizados.")
        return

    print(f"Actividades sin streams: {len(actividades)}")
    token = obtener_access_token()

    conn = get_connection()
    c = conn.cursor()
    procesados = 0

    for act in actividades:
        strava_id = act["strava_id"]
        print(f"  Descargando streams: {act['nombre']} [{act['tipo']}]...")

        streams = obtener_streams(token, strava_id)
        if not streams:
            print(f"  Sin streams para {strava_id}")
            continue

        def get_data(key):
            s = streams.get(key, {})
            return json.dumps(s.get("data", [])) if s else None

        c.execute("""
            INSERT OR IGNORE INTO activity_streams
            (strava_id, time_data, distance_data, heartrate_data,
             velocity_data, altitude_data, cadence_data, latlng_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            strava_id,
            get_data("time"),
            get_data("distance"),
            get_data("heartrate"),
            get_data("velocity_smooth"),
            get_data("altitude"),
            get_data("cadence"),
            get_data("latlng")
        ))
        procesados += 1
        # Respetar rate limit de Strava: max 100 req/15min
        time.sleep(1.5)

    conn.commit()
    conn.close()
    print(f"\nStreams guardados: {procesados} de {len(actividades)}")

if __name__ == "__main__":
    print("Sincronizando streams de Strava...")
    sincronizar_streams()