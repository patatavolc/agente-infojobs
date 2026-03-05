"""
Cliente para la API real de Adzuna
"""

import requests
from typing import Dict, List, Optional
from src.clients.base_client import JobPortalClient
from src.config import AdzunaConfig
import logging

logger = logging.getLogger(__name__)

class AdzunaRealClient(JobPortalClient):
    """
    Endpoints principales:
    - GET /jobs/{country}/search/{page}
    """

    def __init__(self, portal_name):
        super().__init__(portal_name="Adzuna")
        self.app_id = AdzunaConfig.APP_ID
        self.app_key = AdzunaConfig.APP_KEY
        self.base_url = AdzunaConfig.BASE_URL
        self.country = "es"

        if not self.app_id or not self.app_key:
            raise ValueError("Adzuna APP_ID y APP_KEY deben estar configurados en el .env")
        logger.info(f"  ✅ AdzunaRealClient inicializado para {self.country}")

    def buscar_ofertas(
        self,
        query: str,
        provincia_id: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> Dict:
        """
        Busca ofertas en Adzuna API

        Args:
            query: Termino de busqueda (ej: "Python Developer")
            provincia_id: ID de la provincia para filtrar resultados (ej: "33" para Madrid) opcional
            limit: Numero maximo de ofertas a devolver (default: 10)
            **kwargs: Otros parametros especificos de Adzuna (ej: categoria_id, salario_minimo, etc)

        Returns:
            Diccionario con formato estandar del sistema
        """

        try:
            # Convertir provincia_id a nombre de ciudad si existe
            location = self._provincia_id_to_location(provincia_id)
            if kwargs.get('location'):
                location = kwargs['location']
            
            # Parametros de busqueda
            params = {
                'app_id': self.app_id,
                'app_key': self.app_key,
                'results_per_page': min(limit, 50), # Maximo 50 por pagina
                'what': query,
                'content-type': 'application/json'
            }

            # Agregar ubicacion si existe
            if location:
                params['where'] = location
            
            # Parametros opcionales
            if kwargs.get('salary_min'):
                params['salary_min'] = kwargs['salary_min']
            
            if kwargs.get('category'):
                params['category'] = kwargs['category']
            
            if kwargs.get('full_time'):
                params['full_time'] = 1
            
            # Construir la URL
            url = f"{self.base_url}jobs/{self.country}/search/1"

            logger.info(f"Buscando en Adzuna: {query} en {location or 'toda España'}")

            # Realizar la peticion
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json

            # Convertir al formato estandar
            ofertas_formateadas = self._convertir_a_formato_estandar(data, provincia_id)

            logger.info(f"Adzuna: {ofertas_formateadas['totalResults']} ofertas encontradas")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error en Adzuna API: {str(e)}")
            return {
                "totalResults": 0,
                "currentResults": 0,
                "items": [],
                "error": str(e)
            }
    
    def _convertir_a_formato_estandar(self, data: Dict, provincia_id: Optional[str]) -> Dict:
        """
        Convierte la respuesta de Adzuna al formato estandar del sistema

        Formato Adzuna:
        {
            "count": 123,
            "results": [
                {
                    "id": "1234567",
                    "title": "Python Developer",
                    "company": {"display_name": "Tech Corp"},
                    "location": {"display_name": "Madrid, Community of Madrid"},
                    "description": "...",
                    "created": "2024-01-15T10:30:00Z",
                    "redirect_url": "https://...",
                    "salary_min": 30000,
                    "salary_max": 45000,
                    "contract_type": "permanent",
                    "category": {"label": "IT Jobs"}
                }
            ]
        }
        """
        ofertas_raw = data.get('results', [])

        ofertas_formateadas = []
        for oferta in ofertas_raw:
            # Formatear salario
            salary = self._formatear_salario(
                oferta.get('salary_min'),
                oferta.get('salary_max')
            )

            # Extraer ubicacion
            location_info = self._extrar_ubicacion(oferta.get('location', {}))

            oferta_formateada = {
                'id': f"adzuna_{oferta.get('id', 'unknown')}",
                'title': oferta.get('title', 'Sin titulo'),
                'company': oferta.get('company', {}).get('display_name', 'No especificado'),
                'city': location_info['city'],
                'province': {
                    'value': provincia_id or location_info['provincia_id']
                },
                'salary': salary,
                'description': oferta.get('description', '')[:500], # Limitar descripcion
                'url':oferta.get('redirect_url', ''),
                'published_at': oferta.get('created'),
                'contract_type': oferta.get('contract_type', 'No especificado'),
                'category': oferta.get('category', {}).get('label', 'General'),
                # Datos adicionales específicos de Adzuna
                'adzuna_data': {
                    'salary_is_predicted': oferta.get('salary_is_predicted', False),
                    'contract_time': oferta.get('contract_time'),
                    'category_tag': oferta.get('category', {}).get('tag')
                }
            }
        ofertas_formateadas.append(oferta_formateada)

        return {
            'totalResults': data.get('count', 0),
            'currentResults': len(ofertas_formateadas),
            'items': ofertas_formateadas
        }
