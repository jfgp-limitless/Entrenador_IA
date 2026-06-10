from database import get_connection
conn = get_connection()
conn.execute("DROP TABLE IF EXISTS eventos")
conn.commit()
conn.close()
print("Tabla eventos borrada")