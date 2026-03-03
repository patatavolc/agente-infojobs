import time
import random

class InfoJobsClient:
  """Cliente simulado para pruebas cuando la API no esta disponible"""

  def __init__(self):
    # Aqui se cargaran las llaves del .env
    print("InfoJobsClient inicializado. Simulando API...")

  def buscar_ofertas(self, query: str, provincia_id: str = None):
    """Simula una peticion a https://api.infojobs.net/api/9/offer"""
    print(f"DEBUG: Buscando '{query}' en provincia ID {provincia_id}")

    time.sleep(1)

    # Base de datos "falsa" de ofertas
    db_falsa = [
      {"title": f"Desarrollador {query}", "company": "Tech Solutions S.L.", "city": "Madrid", "salary": "30.000€ - 35.000€"},
      {"title": f"Experto en {query} Senior", "company": "Global Data Corp", "city": "Barcelona", "salary": "45.000€ - 55.000€"},
      {"title": f"Junior {query} (Híbrido)", "company": "Startup Innovate", "city": "Valencia", "salary": "22.000€ - 26.000€"},
      {"title": f"Consultor de {query}", "company": "Business Pro", "city": "Sevilla", "salary": "No especificado"}
    ]
  
    # Filtros para que parezca real
    resultados = [o for o in db_falsa if query.lower() in o['title'].lower()]

    # Si no hay resultados exactos, devolvemos la DB completa para probar
    if not resultados:
      resultados = db_falsa
    
    return {
      "totalResults": len(resultados),
      "items": resultados[:random.randint(2, 4)]
    }