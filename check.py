# check.py

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dashboard'))
sys.path.insert(0, os.path.dirname(__file__))

from app import construir_contexto

ctx = construir_contexto()
print(ctx)
print(f"\n{'='*50}")
print(f"Total caracteres: {len(ctx)}")
print(f"Tokens estimados: ~{len(ctx)//4}")



"""
# check.py borrar evento
from database import get_connection
conn = get_connection()
conn.execute("DELETE FROM eventos")
conn.commit()
conn.close()
print("Eventos borrados")
"""