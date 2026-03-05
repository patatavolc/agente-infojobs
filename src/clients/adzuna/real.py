"""
Cliente ASÍNCRONO para la API real de Adzuna
Documentación: https://developer.adzuna.com/overview
"""

import httpx
from typing import Dict, List, Optional
from src.clients.base_client import JobPortalClient
from src.config import AdzunaConfig
import logging

logger = logging.getLogger(__name__)

class AdzunaRealClient(JobPortalClient):
    """
    Cliente asíncrono para Adzuna API
    Endpoints principales:
    - GET /jobs/{country}/search/{page}
    """

    def __init__(self):
        super().__init__(portal_name="Adzuna")
        self.app_id = AdzunaConfig.APP_ID
        self.app_key = AdzunaConfig.APP_KEY
        self.base_url = AdzunaConfig.BASE_URL
        self.country = "es"

        if not self.app_id or not self.app_key:
            raise ValueError("Adzuna APP_ID y APP_KEY deben estar configurados en el .env")
        
        # Cliente HTTP asíncrono reutilizable
        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info(f"✅ AdzunaRealClient inicializado (async) para {self.country}")

    async def buscar_ofertas(
        self,
        query: str,
        provincia_id: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> Dict:
        """
        Busca ofertas en Adzuna API de forma ASÍNCRONA

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

            logger.info(f"🔍 Buscando en Adzuna: {query} en {location or 'toda España'}")

            # Realizar la peticion ASÍNCRONA
            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Convertir al formato estandar
            ofertas_formateadas = self._convertir_a_formato_estandar(data, provincia_id)

            logger.info(f"✅ Adzuna: {ofertas_formateadas['totalResults']} ofertas encontradas")
            
            return ofertas_formateadas
            
        except httpx.HTTPError as e:
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
            location_info = self._extraer_ubicacion(oferta.get('location', {}))

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

    def _formatear_salario(self, salary_min: Optional[float], salary_max: Optional[float]) -> str:
        """Formatea el rango salarial"""
        if not salary_min and not salary_max:
            return "No especificado"
        
        if salary_min and salary_max:
            return f"{int(salary_min):,}€ - {int(salary_max):,}€"
        elif salary_min:
            return f"Desde {int(salary_min):,}€"
        else:
            return f"Hasta {int(salary_max):,}€"
    
    def _extraer_ubicacion(self, location: Dict) -> Dict:
        """
        Extrae ciudad y provincia del objeto location de Adzuna

        Ejemplo: "Madrid, Community of Madrid" -> Madrid
        """
        display_name = location.get('display_name', '')

        # Intentar extraer ciudad (primera parte antes de la coma)
        parts = display_name.split(',')
        city = parts[0].strip() if parts else 'España'

        # Mapear a ID de provincia (simplificado)
        provincia_mapping = {
            'madrid': '33',
            'barcelona': '8',
            'valencia': '46',
            'sevilla': '41',
            'zaragoza': '50',
            'málaga': '29',
            'murcia': '30',
            'bilbao': '48',
            'alicante': '3',
            'córdoba': '14'
        }

        provincia_id = None
        city_lower = city.lower()
        for key, value in provincia_mapping.items():
            if key in city_lower:
                provincia_id = value
                break
        
        return {
            'city': city,
            'provincia_id': provincia_id
        }

    def _provincia_id_to_location(self, provincia_id: Optional[str]) -> Optional[str]:
        """Convierte ID de provincia de infoJobs a nombre de ciudad para Adzuna"""
        if not provincia_id:
            return None
        
        # Mapeo inverso de IDs a nombres de ciudades principales
        mapping = {
            '33': 'Madrid',
            '8': 'Barcelona',
            '46': 'Valencia',
            '41': 'Sevilla',
            '50': 'Zaragoza',
            '29': 'Málaga',
            '30': 'Murcia',
            '48': 'Bilbao',
            '3': 'Alicante',
            '14': 'Córdoba',
            '18': 'Granada',
            '11': 'Cádiz',
            '43': 'Tarragona',
            '17': 'Girona',
            '36': 'Pontevedra',
            '15': 'A Coruña',
            '39': 'Santander',
            '5': 'Oviedo'
        }

        return mapping.get(provincia_id)

    async def get_categories(self) -> List[Dict]:
        """
        Obtiene las categorias disponibles en Adzuna de forma ASÍNCRONA

        Returns:
            Lista de categorias con id y nombre
        """

        try:
            url = f"{self.base_url}jobs/{self.country}/categories"
            params = {
                'app_id': self.app_id,
                'app_key': self.app_key
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            return data.get('results', [])
        except Exception as e:
            logger.error(f"Error obteniendo categorias de Adzuna: {str(e)}")
            return []
    
    async def close(self):
        """Cierra el cliente HTTP asíncrono"""
        await self.client.aclose()
        logger.info("🔒 Cliente Adzuna cerrado")