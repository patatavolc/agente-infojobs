"""Clientes para la API de Adzuna (real y mock)."""

from .real import AdzunaRealClient
from .mock import AdzunaMockClient

__all__ = ["AdzunaRealClient", "AdzunaMockClient"]
