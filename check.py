# check.py
""""
from database import get_connection
conn = get_connection()
conn.execute("DELETE FROM workouts_fuerza")
conn.commit()
conn.close()
print("Listo")
"""

from database import get_connection
import json

conn = get_connection()
rows = conn.execute("SELECT DISTINCT ejercicios_json FROM workouts_fuerza").fetchall()
nombres = set()
for r in rows:
    for e in json.loads(r["ejercicios_json"]):
        if "squat" in e["nombre"].lower():
            nombres.add(e["nombre"])
conn.close()
print(nombres)