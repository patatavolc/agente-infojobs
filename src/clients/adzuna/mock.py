"""
Cliente simulado ASÍNCRONO de Adzuna para testing sin consumir API
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, Optional
from src.clients.base_client import JobPortalClient
import logging

logger = logging.getLogger(__name__)

class AdzunaMockClient(JobPortalClient):
    """Cliente mock que simula respuestas de Adzuna de forma asíncrona"""
    
    def __init__(self):
        super().__init__(portal_name="Adzuna (Mock)")
        self.is_mock = True
        logger.info("⚠️  AdzunaMockClient inicializado (modo simulación)")
    
    async def buscar_ofertas(
        self, 
        query: str, 
        provincia_id: Optional[str] = None, 
        limit: int = 10, 
        **kwargs
    ) -> Dict:
        """Simula búsqueda en Adzuna de forma asíncrona"""
        logger.info(f"🎭 Mock Adzuna: Simulando búsqueda '{query}'")
        
        # Simular latencia de red de forma asíncrona
        await asyncio.sleep(0.5)
        
        # Mapeo de provincias a ciudades
        provincias = {
            '33': 'Madrid',
            '8': 'Barcelona',
            '46': 'Valencia',
            '41': 'Sevilla',
            '29': 'Málaga',
            '50': 'Zaragoza',
            '30': 'Murcia',
            '48': 'Bilbao'
        }
        
        ciudad = provincias.get(provincia_id, 'Madrid')
        
        # Base de datos simulada
        fecha_base = datetime.now()
        ofertas_mock = []
        
        num_ofertas = random.randint(2, min(limit, 5))
        
        for i in range(num_ofertas):
            salary_min = random.randint(20, 50) * 1000
            salary_max = salary_min + random.randint(5, 15) * 1000
            
            ofertas_mock.append({
                'id': f"adzuna_{random.randint(100000, 999999)}",
                'title': f"{query.title()} - {random.choice(['Senior', 'Junior', 'Mid-level'])}",
                'company': random.choice([
                    'Tech Innovators S.L.',
                    'Digital Solutions',
                    'Future Corp',
                    'Smart Systems',
                    'Code Masters',
                    'Data Wizards'
                ]),
                'city': ciudad,
                'province': {'value': provincia_id or '33'},
                'salary': f"{salary_min:,}€ - {salary_max:,}€",
                'description': f"Buscamos profesional de {query} con experiencia en desarrollo y buenas habilidades de comunicación. Proyecto innovador en empresa consolidada.",
                'url': f"https://www.adzuna.es/details/{random.randint(1000000, 9999999)}",
                'published_at': (fecha_base - timedelta(days=random.randint(1, 10))).isoformat(),
                'contract_type': random.choice(['permanent', 'contract', 'temporary']),
                'category': 'IT Jobs',
                'adzuna_data': {
                    'salary_is_predicted': random.choice([True, False]),
                    'contract_time': random.choice(['full_time', 'part_time']),
                    'category_tag': 'it-jobs'
                }
            })
        
        return {
            'totalResults': random.randint(50, 200),
            'currentResults': len(ofertas_mock),
            'items': ofertas_mock
        }
    
    async def close(self):
        """No-op para mantener interfaz consistente"""
        logger.info("🎭 Mock Adzuna cerrado")
