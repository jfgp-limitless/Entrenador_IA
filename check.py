# check.py

from database import get_connection
conn = get_connection()
conn.execute("DELETE FROM workouts_fuerza")
conn.commit()
conn.close()
print("Listo")
