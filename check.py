# check.py
from database import get_connection
conn = get_connection()
conn.execute("DELETE FROM actividades")
conn.execute("DELETE FROM workouts_fuerza")
conn.execute("DELETE FROM activity_streams")
conn.commit()
conn.close()
print("Listo")