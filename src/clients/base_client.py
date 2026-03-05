"""
Clase base abstracta ASÍNCRONA para todos los clientes de portales de empleo
Define la interfaz comun que deben implementar todos los clientes
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class JobPortalClient(ABC):
    """
    Interfaz base ASÍNCRONA para clientes de portales de empleo
    Todos los clientes (mock o real) deben heredar esta clase
    """

    def __init__(self, portal_name: str):
        self.portal_name = portal_name
        self.is_mock = False
    
    @abstractmethod
    async def buscar_ofertas(
        self, 
        query: str, 
        provincia_id: Optional[str] = None, 
        limit: int = 10, 
        **kwargs) -> Dict:
        """
        Busca ofertas de empleo de forma ASÍNCRONA

        Args:
            query: Termino de busqueda (ej: "Python Developer")
            provincia_id: ID de la provincia para filtrar resultados (ej: "33" para Madrid) opcional
            limit: Numero maximo de ofertas a devolver (default: 10)
            **kwargs: Otros parametros especificos de cada portal (ej: categoria_id, salario_minimo, etc)

        Returns:
            Diccionario con estructura:
            {
                "totalResults": int,
                "currentResults": int,
                "items": List[Dict]
            }
        """
        pass
    
    def get_portal_name(self) -> str:
        """Retorna el nombre del portal"""
        return self.portal_name
