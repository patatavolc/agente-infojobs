"""
Cliente simulado ASÍNCRONO de InfoJobs para pruebas cuando la API no está disponible
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, Optional
from src.clients.base_client import JobPortalClient
import logging

logger = logging.getLogger(__name__)

class InfoJobsMockClient(JobPortalClient):
    """Cliente mock que simula la API de InfoJobs de forma asíncrona"""

    def __init__(self):
        super().__init__(portal_name="InfoJobs (Mock)")
        self.is_mock = True
        logger.info("⚠️  InfoJobsMockClient inicializado (modo simulación)")

    async def buscar_ofertas(
        self, 
        query: str, 
        provincia_id: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> Dict:
        """Simula una petición a la API de InfoJobs de forma asíncrona"""
        logger.info(f"🎭 Mock InfoJobs: Buscando '{query}' en provincia ID {provincia_id}")

        # Simular latencia de red
        await asyncio.sleep(0.8)

        # Mapeo de IDs a provincias para el mock
        provincias_map = {
            "33": "Madrid", "8": "Barcelona", "46": "Valencia", 
            "41": "Sevilla", "29": "Málaga", "48": "Vizcaya",
            "50": "Zaragoza", "30": "Murcia", "3": "Alicante"
        }

        ciudad = provincias_map.get(provincia_id, "Madrid")

        # Base de datos "falsa" de ofertas con fecha
        fecha_base = datetime.now()
        db_falsa = [
            {
                "id": f"ij_{random.randint(10000, 99999)}",
                "title": f"Desarrollador {query}",
                "company": "Tech Solutions S.L.",
                "city": ciudad,
                "province": {"value": provincia_id or "33"},
                "salary": "30.000€ - 35.000€",
                "description": f"Desarrollo con {query} en entorno ágil. Stack tecnológico moderno.",
                "url": f"https://www.infojobs.net/oferta/{random.randint(100000, 999999)}",
                "published_at": (fecha_base - timedelta(days=2)).isoformat()
            },
            {
                "id": f"ij_{random.randint(10000, 99999)}",
                "title": f"Experto en {query} Senior",
                "company": "Global Data Corp",
                "city": ciudad,
                "province": {"value": provincia_id or "8"},
                "salary": "45.000€ - 55.000€",
                "description": f"Buscamos experto en {query} para liderar proyectos innovadores.",
                "url": f"https://www.infojobs.net/oferta/{random.randint(100000, 999999)}",
                "published_at": (fecha_base - timedelta(days=5)).isoformat()
            },
            {
                "id": f"ij_{random.randint(10000, 99999)}",
                "title": f"Junior {query} (Híbrido)",
                "company": "Startup Innovate",
                "city": ciudad,
                "province": {"value": provincia_id or "46"},
                "salary": "22.000€ - 26.000€",
                "description": f"Posición junior para aprender {query}. Ambiente dinámico y flexible.",
                "url": f"https://www.infojobs.net/oferta/{random.randint(100000, 999999)}",
                "published_at": (fecha_base - timedelta(days=1)).isoformat()
            },
            {
                "id": f"ij_{random.randint(10000, 99999)}",
                "title": f"Consultor de {query}",
                "company": "Business Pro",
                "city": ciudad,
                "province": {"value": provincia_id or "41"},
                "salary": "No especificado",
                "description": f"Consultoría especializada en {query} para clientes nacionales e internacionales.",
                "url": f"https://www.infojobs.net/oferta/{random.randint(100000, 999999)}",
                "published_at": (fecha_base - timedelta(days=7)).isoformat()
            }
        ]

        # Filtros para que parezca real
        resultados = [o for o in db_falsa if query.lower() in o['title'].lower()]

        # Si no hay resultados exactos, devolvemos la DB completa para probar
        if not resultados:
            resultados = db_falsa

        num_results = random.randint(2, min(len(resultados), limit))
        
        return {
            "totalResults": len(resultados),
            "currentResults": num_results,
            "items": resultados[:num_results]
        }
    
    async def close(self):
        """No-op para mantener interfaz consistente"""
        logger.info("🎭 Mock InfoJobs cerrado")
