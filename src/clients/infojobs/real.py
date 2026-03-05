"""
Cliente ASÍNCRONO para la API real de InfoJobs
Documentación: https://developer.infojobs.net/
"""

import httpx
import base64
from typing import Dict, Optional
from src.clients.base_client import JobPortalClient
from src.config import InfoJobsConfig
import logging

logger = logging.getLogger(__name__)

class InfoJobsRealClient(JobPortalClient):
    """
    Cliente asíncrono para la API real de InfoJobs
    Requiere CLIENT_ID y CLIENT_SECRET configurados en .env
    """

    def __init__(self):
        super().__init__(portal_name="InfoJobs")
        self.client_id = InfoJobsConfig.CLIENT_ID
        self.client_secret = InfoJobsConfig.CLIENT_SECRET
        self.base_url = InfoJobsConfig.BASE_URL

        if not self.client_id or not self.client_secret:
            raise ValueError("InfoJobs CLIENT_ID y CLIENT_SECRET deben estar configurados en .env")

        # Preparar autenticación Basic
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        # Cliente HTTP asíncrono con headers de autenticación
        self.client = httpx.AsyncClient(
            timeout=10.0,
            headers={
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json"
            }
        )
        logger.info("✅ InfoJobsRealClient inicializado (async)")

    async def buscar_ofertas(
        self,
        query: str,
        provincia_id: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> Dict:
        """
        Busca ofertas en la API real de InfoJobs de forma ASÍNCRONA

        Args:
            query: Palabra clave de búsqueda
            provincia_id: ID de provincia de InfoJobs (ej: "33" para Madrid)
            limit: Número máximo de resultados (default: 10, max: 50)
            **kwargs: Parámetros adicionales:
                - category: ID de categoría
                - subcategory: ID de subcategoría
                - salaryMin: Salario mínimo
                - teleworking: Nivel de teletrabajo (1-5)

        Returns:
            Diccionario con formato estándar del sistema
        """
        try:
            # Construir parámetros de búsqueda
            params = {
                'q': query,
                'maxResults': min(limit, 50)  # InfoJobs permite máximo 50
            }

            if provincia_id:
                params['province'] = provincia_id

            # Parámetros opcionales
            if kwargs.get('category'):
                params['category'] = kwargs['category']
            
            if kwargs.get('subcategory'):
                params['subcategory'] = kwargs['subcategory']
            
            if kwargs.get('salaryMin'):
                params['salaryMin'] = kwargs['salaryMin']
            
            if kwargs.get('teleworking'):
                params['teleworking'] = kwargs['teleworking']

            # Endpoint de búsqueda de ofertas
            url = f"{self.base_url}offer"

            logger.info(f"🔍 Buscando en InfoJobs (REAL): {query} en provincia {provincia_id or 'todas'}")

            # Realizar petición asíncrona
            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Convertir al formato estándar
            ofertas_formateadas = self._convertir_a_formato_estandar(data)

            logger.info(f"✅ InfoJobs (REAL): {ofertas_formateadas['totalResults']} ofertas encontradas")

            return ofertas_formateadas

        except httpx.HTTPError as e:
            logger.error(f"❌ Error en InfoJobs API: {str(e)}")
            return {
                "totalResults": 0,
                "currentResults": 0,
                "items": [],
                "error": str(e)
            }

    def _convertir_a_formato_estandar(self, data: Dict) -> Dict:
        """
        Convierte la respuesta de InfoJobs al formato estándar

        Formato InfoJobs:
        {
            "totalResults": 123,
            "currentResults": 10,
            "items": [
                {
                    "id": "abc123",
                    "title": "Desarrollador Python",
                    "province": {"id": 33, "value": "Madrid"},
                    "city": "Madrid",
                    "link": "https://...",
                    "category": {"id": 1, "value": "Informática"},
                    "contractType": {"id": 1, "value": "Indefinido"},
                    "salaryMin": {"amount": 30000},
                    "salaryMax": {"amount": 40000},
                    "published": "2024-01-15T10:30:00.000Z",
                    "updated": "2024-01-16T14:20:00.000Z",
                    "author": {"name": "Empresa S.L."}
                }
            ]
        }
        """
        ofertas_raw = data.get('items', [])
        ofertas_formateadas = []

        for oferta in ofertas_raw:
            # Formatear salario
            salary = self._formatear_salario(oferta)

            # Extraer provincia
            province_data = oferta.get('province', {})
            province_id = str(province_data.get('id', '')) if isinstance(province_data, dict) else None

            oferta_formateada = {
                'id': oferta.get('id', 'unknown'),
                'title': oferta.get('title', 'Sin título'),
                'company': oferta.get('author', {}).get('name', 'No especificado'),
                'city': oferta.get('city', 'No especificado'),
                'province': {
                    'value': province_id,
                    'name': province_data.get('value', '') if isinstance(province_data, dict) else ''
                },
                'salary': salary,
                'description': oferta.get('snippet', '')[:500],  # Snippet es el resumen
                'url': oferta.get('link', ''),
                'published_at': oferta.get('published'),
                'updated_at': oferta.get('updated'),
                'contract_type': oferta.get('contractType', {}).get('value', 'No especificado'),
                'category': oferta.get('category', {}).get('value', 'General'),
                # Datos adicionales de InfoJobs
                'infojobs_data': {
                    'teleworking': oferta.get('teleworking', {}).get('value'),
                    'study': oferta.get('study', {}).get('value'),
                    'experienceMin': oferta.get('experienceMin', {}).get('value'),
                    'workDay': oferta.get('workDay', {}).get('value')
                }
            }
            ofertas_formateadas.append(oferta_formateada)

        return {
            'totalResults': data.get('totalResults', 0),
            'currentResults': len(ofertas_formateadas),
            'items': ofertas_formateadas
        }

    def _formatear_salario(self, oferta: Dict) -> str:
        """Extrae y formatea el salario de la oferta"""
        salary_min = oferta.get('salaryMin', {})
        salary_max = oferta.get('salaryMax', {})

        min_amount = salary_min.get('amount') if isinstance(salary_min, dict) else None
        max_amount = salary_max.get('amount') if isinstance(salary_max, dict) else None

        if not min_amount and not max_amount:
            # Intentar con el periodo salarial
            salary_period = oferta.get('salaryPeriod', {}).get('value', '')
            if salary_period:
                return salary_period
            return "No especificado"

        if min_amount and max_amount:
            return f"{int(min_amount):,}€ - {int(max_amount):,}€"
        elif min_amount:
            return f"Desde {int(min_amount):,}€"
        elif max_amount:
            return f"Hasta {int(max_amount):,}€"
        
        return "No especificado"

    async def close(self):
        """Cierra el cliente HTTP asíncrono"""
        await self.client.aclose()
        logger.info("🔒 Cliente InfoJobs cerrado")
