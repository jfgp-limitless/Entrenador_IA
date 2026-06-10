from database import get_connection
import json

conn = get_connection()
row = conn.execute("""
    SELECT velocity_data FROM activity_streams 
    WHERE strava_id = '18868963840'
""").fetchone()

vel = json.loads(row['velocity_data'] or '[]')
non_zero = [v for v in vel if v and v > 0.5]
print(f"Total puntos: {len(vel)}")
print(f"Puntos con velocidad >0.5: {len(non_zero)}")
print(f"Primeros 10: {vel[:10]}")
print(f"Max velocidad: {max(vel) if vel else 0}")