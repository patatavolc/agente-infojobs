"""
Modulo de clientes para diferentes portales de emploe
Soporta tantos modos mock como APIs reales
"""

from .base_client import JobsPortalClient
from .infojobs_mock import InfoJobsMockClient
from .infojobs_real import InfoJobsRealClient

__all__ = [
    "JobsPortalClient",
    "InfoJobsMockClient",
    "InfoJobsRealClient"
]