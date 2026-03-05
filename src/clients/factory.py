"""
Factory para crear clientes de portales de empleo
Decide qué cliente usar según configuración y disponibilidad
"""

from typing import List
from src.clients.base_client import JobPortalClient
from src.config import InfoJobsConfig, AdzunaConfig
import logging

logger = logging.getLogger(__name__)


class ClientFactory:
    """
    Factory centralizada para crear clientes de portales de empleo
    Maneja la lógica de decidir entre clientes reales o mock
    """

    _infojobs_client = None  # Singleton para reutilizar la instancia
    _adzuna_client = None  # Singleton para reutilizar la instancia

    @staticmethod
    def create_infojobs_client() -> JobPortalClient:
        """
        Crea o devuelve el cliente de InfoJobs
        Usa el cliente real si las credenciales están configuradas,
        si no, usa el cliente mock
        
        Returns:
            Cliente de InfoJobs (real o mock)
        """
        if ClientFactory._infojobs_client is not None:
            return ClientFactory._infojobs_client

        if InfoJobsConfig.is_configured():
            logger.info("🔌 Creando cliente REAL de InfoJobs")
            try:
                from src.clients.infojobs.real import InfoJobsRealClient
                ClientFactory._infojobs_client = InfoJobsRealClient()
                logger.info("✅ Cliente REAL de InfoJobs inicializado")
            except (ImportError, ValueError) as e:
                logger.warning(f"⚠️  No se pudo cargar cliente real: {e}. Usando MOCK")
                from src.clients.infojobs.mock import InfoJobsMockClient
                ClientFactory._infojobs_client = InfoJobsMockClient()
        else:
            logger.info("🎭 Credenciales de InfoJobs no configuradas. Usando cliente MOCK")
            from src.clients.infojobs.mock import InfoJobsMockClient
            ClientFactory._infojobs_client = InfoJobsMockClient()

        return ClientFactory._infojobs_client

    @staticmethod
    def create_adzuna_client() -> JobPortalClient:
        """
        Crea o devuelve el cliente de Adzuna
        Usa el cliente real si las credenciales están configuradas,
        si no, usa el cliente mock
        
        Returns:
            Cliente de Adzuna (real o mock)
        """
        if ClientFactory._adzuna_client is not None:
            return ClientFactory._adzuna_client

        if AdzunaConfig.is_configured():
            logger.info("🔌 Creando cliente REAL de Adzuna")
            try:
                from src.clients.adzuna.real import AdzunaRealClient
                ClientFactory._adzuna_client = AdzunaRealClient()
                logger.info("✅ Cliente REAL de Adzuna inicializado")
            except (ImportError, ValueError) as e:
                logger.warning(f"⚠️  No se pudo cargar cliente real: {e}. Usando MOCK")
                from src.clients.adzuna.mock import AdzunaMockClient
                ClientFactory._adzuna_client = AdzunaMockClient()
        else:
            logger.info("🎭 Credenciales de Adzuna no configuradas. Usando cliente MOCK")
            from src.clients.adzuna.mock import AdzunaMockClient
            ClientFactory._adzuna_client = AdzunaMockClient()

        return ClientFactory._adzuna_client

    @staticmethod
    def get_available_portals() -> List[str]:
        """
        Devuelve una lista de portales disponibles según la configuración
        
        Returns:
            Lista de nombres de portales disponibles
        """
        portales = []

        # InfoJobs siempre disponible (al menos en modo mock)
        if InfoJobsConfig.is_configured():
            portales.append("InfoJobs (REAL)")
        else:
            portales.append("InfoJobs (MOCK)")

        # Adzuna
        if AdzunaConfig.is_configured():
            portales.append("Adzuna (REAL)")
        else:
            portales.append("Adzuna (MOCK)")

        return portales

    @staticmethod
    async def close_all_clients():
        """
        Cierra todos los clientes abiertos (importante para liberar recursos)
        """
        if ClientFactory._infojobs_client:
            await ClientFactory._infojobs_client.close()
        if ClientFactory._adzuna_client:
            await ClientFactory._adzuna_client.close()
        
        logger.info("🔒 Todos los clientes cerrados")

    @staticmethod
    def reset_clients():
        """
        Resetea los clientes singleton (útil para testing)
        """
        ClientFactory._infojobs_client = None
        ClientFactory._adzuna_client = None
        logger.info("🔄 Clientes reseteados")


# Testing
if __name__ == "__main__":
    import asyncio
    
    async def main():
        logging.basicConfig(level=logging.INFO)
        
        print("=" * 60)
        print("Prueba de ClientFactory")
        print("=" * 60)
        
        # Mostrar portales disponibles
        portales = ClientFactory.get_available_portals()
        print(f"\n📋 Portales disponibles:")
        for portal in portales:
            print(f"  - {portal}")
        
        # Crear clientes
        print("\n🔧 Creando clientes...")
        infojobs_client = ClientFactory.create_infojobs_client()
        adzuna_client = ClientFactory.create_adzuna_client()
        
        print(f"✅ InfoJobs: {infojobs_client.portal_name} (Mock: {infojobs_client.is_mock})")
        print(f"✅ Adzuna: {adzuna_client.portal_name} (Mock: {adzuna_client.is_mock})")
        
        # Probar búsqueda
        print("\n🔍 Probando búsqueda en InfoJobs...")
        resultados_ij = await infojobs_client.buscar_ofertas(query="python", provincia_id="33", limit=3)
        print(f"   Resultados InfoJobs: {resultados_ij['totalResults']} ofertas")
        
        print("\n🔍 Probando búsqueda en Adzuna...")
        resultados_az = await adzuna_client.buscar_ofertas(query="python", provincia_id="33", limit=3)
        print(f"   Resultados Adzuna: {resultados_az['totalResults']} ofertas")
        
        # Cerrar clientes
        print("\n🔒 Cerrando clientes...")
        await ClientFactory.close_all_clients()
        print("✅ Prueba completada")
    
    asyncio.run(main())
