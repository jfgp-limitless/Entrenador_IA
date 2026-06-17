# check.py
"""""
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