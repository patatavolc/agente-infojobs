"""Clientes para la API de InfoJobs (real y mock)."""

from .real import InfoJobsRealClient
from .mock import InfoJobsMockClient

__all__ = ["InfoJobsRealClient", "InfoJobsMockClient"]
