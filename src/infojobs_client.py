import time
import random
from datetime import datetime, timedelta

class InfoJobsClient:
  """Cliente simulado para pruebas cuando la API no esta disponible"""

  def __init__(self):
    # Aqui se cargaran las llaves del .env
    print("InfoJobsClient inicializado. Simulando API...")

  def buscar_ofertas(self, query: str, provincia_id: str = None):
    """Simula una peticion a https://api.infojobs.net/api/9/offer"""
    print(f"DEBUG: Buscando '{query}' en provincia ID {provincia_id}")

    time.sleep(1)

    # Mapeo de IDs a provincias para el mock
    provincias_map = {
        "33": "Madrid", "8": "Barcelona", "46": "Valencia", 
        "41": "Sevilla", "29": "Málaga", "48": "Vizcaya"
    }

    ciudad = provincias_map.get(provincia_id, "Madrid")

    # Base de datos "false" de ofertas con fecha
    fecha_base = datetime.now()
    db_falsa = [
        {
                "id": f"ij_{random.randint(10000, 99999)}",
                "title": f"Desarrollador {query}",
                "company": "Tech Solutions S.L.",
                "city": ciudad,
                "province": {"value": provincia_id or "33"},
                "salary": "30.000€ - 35.000€",
                "published_at": (fecha_base - timedelta(days=2)).isoformat()
            },
            {
                "id": f"ij_{random.randint(10000, 99999)}",
                "title": f"Experto en {query} Senior",
                "company": "Global Data Corp",
                "city": ciudad,
                "province": {"value": provincia_id or "8"},
                "salary": "45.000€ - 55.000€",
                "published_at": (fecha_base - timedelta(days=5)).isoformat()
            },
            {
                "id": f"ij_{random.randint(10000, 99999)}",
                "title": f"Junior {query} (Híbrido)",
                "company": "Startup Innovate",
                "city": ciudad,
                "province": {"value": provincia_id or "46"},
                "salary": "22.000€ - 26.000€",
                "published_at": (fecha_base - timedelta(days=1)).isoformat()
            },
            {
                "id": f"ij_{random.randint(10000, 99999)}",
                "title": f"Consultor de {query}",
                "company": "Business Pro",
                "city": ciudad,
                "province": {"value": provincia_id or "41"},
                "salary": "No especificado",
                "published_at": (fecha_base - timedelta(days=7)).isoformat()
            }
    ]

    # Filtros para que parezca real
    resultados = [o for o in db_falsa if query.lower() in o['title'].lower()]

    # Si no hay resultados exactos, devolvemos la DB completa para probar
    if not resultados:
        resultados = db_falsa

    return {
        "totalResults": len(resultados),
        "currentResults": random.randint(2, 4),
        "items": resultados[:random.randint(2, 4)]
    }
