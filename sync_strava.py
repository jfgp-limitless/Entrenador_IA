import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from database import get_connection, crear_tablas

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
    if response.status_code != 200:
        print(f"Error obteniendo token: {response.text}")
        return None
    return response.json()["access_token"]

def metros_a_km(metros):
    return round(metros / 1000, 2) if metros else 0

def segundos_a_min(segundos):
    return round(segundos / 60, 1) if segundos else 0

def obtener_detalle_actividad(access_token, strava_id):
    """Obtiene descripción completa de una actividad individual."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        f"https://www.strava.com/api/v3/activities/{strava_id}",
        headers=headers
    )
    if response.status_code == 200:
        data = response.json()
        return {
            "descripcion": data.get("description", ""),
            "calorias": data.get("calories") or data.get("kilojoules")
        }
    return {"descripcion": "", "calorias": None}
   

def sincronizar_actividades(access_token, paginas=5):
    headers = {"Authorization": f"Bearer {access_token}"}
    conn = get_connection()
    c = conn.cursor()

    nuevas = 0
    existentes = 0

    for pagina in range(1, paginas + 1):
        response = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers=headers,
            params={"per_page": 50, "page": pagina}
        )

        if response.status_code != 200:
            print(f"Error en página {pagina}: {response.text}")
            break

        actividades = response.json()
        if not actividades:
            break

        for a in actividades:
            strava_id = str(a["id"])

            existe = c.execute(
                "SELECT id FROM actividades WHERE strava_id = ?", (strava_id,)
            ).fetchone()

            if existe:
                existentes += 1
                continue

            fecha = a.get("start_date_local", "")[:10]
            distancia = metros_a_km(a.get("distance", 0))
            tiempo = a.get("moving_time", 0)
            velocidad = round(a.get("average_speed", 0) * 3.6, 2)
            tipo = a.get("type", "") or a.get("sport_type", "")

            # Obtener descripción completa (necesaria para Hevy)
            detalle = obtener_detalle_actividad(access_token, strava_id)
            descripcion = detalle["descripcion"]
            calorias = detalle["calorias"] or a.get("calories")
            print(f"    → {a.get('name', '')} [{tipo}] desc: {len(descripcion)} chars | cal: {calorias}")

            c.execute("""
                INSERT INTO actividades (
                    strava_id, nombre, tipo, fecha,
                    distancia_km, tiempo_segundos, velocidad_media,
                    fc_media, fc_maxima, desnivel_positivo, calorias, descripcion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                strava_id,
                a.get("name", ""),
                tipo,
                fecha,
                distancia,
                tiempo,
                velocidad,
                a.get("average_heartrate"),
                a.get("max_heartrate"),
                a.get("total_elevation_gain"),
                calorias,
                descripcion
            ))
            nuevas += 1

        print(f"  Página {pagina}: {len(actividades)} actividades procesadas")

    conn.commit()
    conn.close()
    return nuevas, existentes
    headers = {"Authorization": f"Bearer {access_token}"}
    conn = get_connection()
    c = conn.cursor()

    nuevas = 0
    existentes = 0

    for pagina in range(1, paginas + 1):
        response = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers=headers,
            params={"per_page": 50, "page": pagina}
        )

        if response.status_code != 200:
            print(f"Error en página {pagina}: {response.text}")
            break

        actividades = response.json()
        if not actividades:
            break

        for a in actividades:
            strava_id = str(a["id"])

            # Verificar si ya existe
            existe = c.execute(
                "SELECT id FROM actividades WHERE strava_id = ?", (strava_id,)
            ).fetchone()

            if existe:
                existentes += 1
                continue

            fecha = a.get("start_date_local", "")[:10]
            distancia = metros_a_km(a.get("distance", 0))
            tiempo = a.get("moving_time", 0)
            velocidad = round(a.get("average_speed", 0) * 3.6, 2)  # m/s a km/h

            c.execute("""
                INSERT INTO actividades (
                    strava_id, nombre, tipo, fecha,
                    distancia_km, tiempo_segundos, velocidad_media,
                    fc_media, fc_maxima, desnivel_positivo, calorias, descripcion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                strava_id,
                a.get("name", ""),
                a.get("type", ""),
                fecha,
                distancia,
                tiempo,
                velocidad,
                a.get("average_heartrate"),
                a.get("max_heartrate"),
                a.get("total_elevation_gain"),
                a.get("calories"),
                a.get("description", "")
            ))
            nuevas += 1

        print(f"  Página {pagina}: {len(actividades)} actividades procesadas")

    conn.commit()
    conn.close()
    return nuevas, existentes

def main():
    print("Sincronizando actividades de Strava...")
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    crear_tablas()

    token = obtener_access_token()
    if not token:
        return

    print("✓ Token obtenido correctamente")
    print("Descargando actividades (últimas 250)...\n")

    nuevas, existentes = sincronizar_actividades(token, paginas=5)

    print(f"\n✓ Sincronización completa")
    print(f"  Actividades nuevas guardadas: {nuevas}")
    print(f"  Actividades ya existentes:    {existentes}")

if __name__ == "__main__":
    main()