from database import get_connection
import json

conn = get_connection()
rows = conn.execute("SELECT ejercicios_json FROM workouts_fuerza").fetchall()

ejercicios = {}
for r in rows:
    for e in json.loads(r['ejercicios_json']):
        nombre = e['nombre']
        musculo = e['musculo']
        if nombre not in ejercicios:
            ejercicios[nombre] = musculo

for nombre, musculo in sorted(ejercicios.items()):
    print(f"  [{musculo:12}] {nombre}")