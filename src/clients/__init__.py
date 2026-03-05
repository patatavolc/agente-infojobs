"""Clientes y factory para APIs de portales de empleo."""

# Nota: Los imports se hacen lazy para evitar dependencias circulares
# Usa: from src.clients.factory import ClientFactory
# O:   from src.clients.infojobs import InfoJobsMockClient

__all__ = [
    "JobPortalClient",
    "ClientFactory",
    "InfoJobsRealClient",
    "InfoJobsMockClient",
    "AdzunaClient",
    "AdzunaMockClient",
]
