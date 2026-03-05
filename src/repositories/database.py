"""
Repositorio ASÍNCRONO para gestionar ofertas de empleo en PostgreSQL
Proporciona metodos async para guardar, buscar y obtener estadisticas
"""

import asyncpg
from typing import List, Dict, Optional
from datetime import datetime
from src.config import DatabaseConfig
import logging
import json

logger = logging.getLogger(__name__)

class JobOffersRepository:
    def __init__(self):
        self.connection_params = DatabaseConfig.get_connection_params()
        self.pool = None
        logger.info(f"JobOffersRepository inicializado para {self.connection_params['dbname']}@{self.connection_params['host']}")

    async def initialize_pool(self):
        """Inicializa el pool de conexiones asíncronas"""
        if self.pool is None:
            dsn = DatabaseConfig.get_dsn()
            self.pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=2,
                max_size=10
            )
            logger.info("✅ Pool de conexiones async inicializado")

    async def get_connection(self):
        """ 
        Obtiene una conexión del pool (para compatibilidad)
        En general, usa self.pool directamente
        
        Returns:
            Conexion asyncpg

        Raises: 
            asyncpg.PostgresError: Si no se puede conectar a la base de datos
        """
        if self.pool is None:
            await self.initialize_pool()
        return await self.pool.acquire()

    async def test_connection(self) -> bool:
        """"
        Prueba la conexion a la base de datos de forma ASÍNCRONA

        Returns:
            True si la conexion es exitosa, False en caso contrario
        """
        try:
            if self.pool is None:
                await self.initialize_pool()
                
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version();")
                logger.info(f"✅ Conexion exitosa a PostgreSQL: {version[:50]}...")

                # Verificar que las tablas existen
                tables = await conn.fetch("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                """)

                table_names = [row['table_name'] for row in tables]
                required_tables = ['job_offers', 'job_portals']
                missing_tables = [t for t in required_tables if t not in table_names]

                if missing_tables:
                    logger.warning(f"⚠️ Tablas faltantes: {', '.join(missing_tables)}")
                    return False

                logger.info(f"✅ Tablas requeridas encontradas: {', '.join(required_tables)}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error al probar la conexion: {e}")
            return False

    async def get_portal_id(self, portal_name: str) -> Optional[int]:
        """
        Obtiene el ID del portal por nombre de forma ASÍNCRONA

        Args:
            portal_name: Nombre del portal (ej: 'InfoJobs)
            
        Returns:
            ID del portal o None si no existe
        """
        if self.pool is None:
            await self.initialize_pool()
            
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT id FROM job_portals WHERE name = $1", 
                portal_name
            )
            return result['id'] if result else None

    async def get_or_create_portal(self, portal_name: str, base_url: str = None) -> int:
        """
        Obtiene o crea un portal de forma ASÍNCRONA
        
        Args:
            portal_name: Nombre del portal
            base_url: URL base del portal, opcional
            
        Returns:
            ID del portal en la base de datos
        """
        portal_id = await self.get_portal_id(portal_name)
        if portal_id:
            return portal_id
        
        if self.pool is None:
            await self.initialize_pool()
            
        async with self.pool.acquire() as conn:
            portal_id = await conn.fetchval(
                "INSERT INTO job_portals (name, base_url) VALUES ($1, $2) RETURNING id",
                portal_name, base_url
            )
            logger.info(f"✅ Portal '{portal_name}' creado con ID {portal_id}")
            return portal_id
    
    async def save_offer(self, offer: Dict, portal_name: str = "InfoJobs") -> bool:
        """
        Guarda una oferta en la base de datos de forma ASÍNCRONA
    
        Args:
            offer: Diccionario con los datos de la oferta
            portal_name: Nombre del portal de origen
            
        Returns:
            True si se guardó exitosamente, False en caso contrario
        """
        portal_id = await self.get_portal_id(portal_name)
        if not portal_id:
            portal_id = await self.get_or_create_portal(portal_name)

        if self.pool is None:
            await self.initialize_pool()

        async with self.pool.acquire() as conn:
            try:
                # Generar ID único si no existe
                external_id = offer.get('id', f"auto_{hash(str(offer))}")
                
                # Extraer provincia - InfoJobs usa objeto, otros portales pueden usar string
                province = None
                if isinstance(offer.get('province'), dict):
                    province = offer['province'].get('value') or offer['province'].get('name')
                else:
                    province = offer.get('province')

                # Parsear fecha de publicación si existe
                published_at = None
                if offer.get('published_at'):
                    try:
                        published_at = datetime.fromisoformat(offer['published_at'].replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        published_at = None

                # Convertir offer dict a JSON para raw_data
                raw_data_json = json.dumps(offer)

                offer_id = await conn.fetchval("""
                    INSERT INTO job_offers
                    (portal_id, external_id, title, company, city, province, salary, 
                    description, url, published_at, raw_data)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb)
                    ON CONFLICT (portal_id, external_id)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        company = EXCLUDED.company,
                        city = EXCLUDED.city,
                        province = EXCLUDED.province,
                        salary = EXCLUDED.salary,
                        description = EXCLUDED.description,
                        url = EXCLUDED.url,
                        published_at = EXCLUDED.published_at,
                        raw_data = EXCLUDED.raw_data,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, 
                    portal_id,
                    external_id,
                    offer.get('title'),
                    offer.get('company'),
                    offer.get('city'),
                    province,
                    offer.get('salary'),
                    offer.get('description'),
                    offer.get('url'),
                    published_at,
                    raw_data_json
                )
                
                logger.debug(f"✅ Oferta '{offer.get('title')}' guardada con ID {offer_id}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Error guardando oferta: {e}")
                return False

    async def save_offer_batch(self, offers: List[Dict], portal_name: str) -> int:
        """
        Guarda multiples ofertas de forma ASÍNCRONA.
        
        Args:
            offers: Lista de diccionarios con los datos de las ofertas
            portal_name: Nombre del portal de origen
        
        Returns:
            Numero de ofertas guardadas exitosamente
        """
        portal_id = await self.get_portal_id(portal_name)
        if not portal_id:
            portal_id = await self.get_or_create_portal(portal_name)
        
        saved_count = 0
        for offer in offers:
            try:
                if await self.save_offer(offer, portal_name):
                    saved_count += 1
            except Exception as e:
                logger.error(f"❌ Error guardando oferta en batch: {e}")
                continue
                
        logger.info(f"✅ Batch guardado: {saved_count}/{len(offers)} ofertas")
        return saved_count

    # search_offer()
    async def search_offers(self, keyword: str, portal_name: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        Busca ofertas por palabra clave de forma ASÍNCRONA
        
        Args:
            keyword: Palabra clave a buscar en título, empresa o descripción
            portal_name: Nombre del portal para filtrar (opcional)
            limit: Número máximo de resultados (default: 100)

        Returns:
            Lista de ofertas que coinciden con la búsqueda
        """
        if self.pool is None:
            await self.initialize_pool()

        portal_id = None
        if portal_name:
            portal_id = await self.get_portal_id(portal_name)
            if not portal_id:
                logger.warning(f"⚠️ Portal '{portal_name}' no encontrado")
        
        async with self.pool.acquire() as conn:
            query = """
                SELECT jo.*, jp.name AS portal_name
                FROM job_offers jo
                JOIN job_portals jp ON jo.portal_id = jp.id
                WHERE (jo.title ILIKE $1 OR jo.company ILIKE $1 OR jo.description ILIKE $1)
            """
            params = [f"%{keyword}%"]
            
            if portal_id:
                query += " AND jo.portal_id = $2"
                params.append(portal_id)
                query += " ORDER BY jo.published_at DESC LIMIT $3"
                params.append(limit)
            else:
                query += " ORDER BY jo.published_at DESC LIMIT $2"
                params.append(limit)
            
            results = await conn.fetch(query, *params)
            logger.info(f"🔍 Búsqueda: {len(results)} ofertas encontradas para '{keyword}'")
            return [dict(row) for row in results]
        
    #get_offer_by_id()
    #get_offer_by_id()
    async def get_offer_by_id(self, offer_id: int) -> Optional[Dict]:
        """
        Obtiene una oferta por su ID de forma ASÍNCRONA
        
        Args:
            offer_id: ID de la oferta en la base de datos
        
        Returns:
            Diccionario con los datos de la oferta o None si no se encuentra
        """
        if self.pool is None:
            await self.initialize_pool()

        if not isinstance(offer_id, int):
            logger.warning(f"⚠️ ID de oferta inválido: {offer_id}")
            return None

        async with self.pool.acquire() as conn:
            offer = await conn.fetchrow("""
                SELECT jo.*, jp.name AS portal_name
                FROM job_offers jo
                JOIN job_portals jp ON jo.portal_id = jp.id
                WHERE jo.id = $1
            """, offer_id)
            
            if offer:
                logger.info(f"✅ Oferta encontrada: ID {offer_id} - {offer['title']}")
                return dict(offer)
            else:
                logger.warning(f"⚠️ Oferta con ID {offer_id} no encontrada")
                return None
        

    #get_recent_offers()
    async def get_recent_offers(self, limit: int = 10) -> List[Dict]:
        """
        Obtiene las ofertas mas recientes de forma ASÍNCRONA

        Args:
            limit: Numero maximo de ofertas a obtener (default: 10)
        
        Returns:
            Lista de ofertas ordenadas por fecha de publicacion descendente
        """
        if self.pool is None:
            await self.initialize_pool()

        if not isinstance(limit, int) or limit <= 0:
            logger.warning(f"⚠️ Limite inválido: {limit}")
            return []

        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT jo.*, jp.name AS portal_name
                FROM job_offers jo
                JOIN job_portals jp ON jo.portal_id = jp.id
                ORDER BY jo.published_at DESC
                LIMIT $1
            """, limit)
            logger.info(f"✅ {len(results)} ofertas recientes obtenidas")
            return [dict(row) for row in results]


    #delete_offers_by_portal()
    async def delete_offers_by_portal(self, portal_name: str) -> int:
        """
        Elimina todas las ofertas asociadas a un portal de forma ASÍNCRONA

        Args:
            portal_name: Nombre del portal cuyas ofertas se eliminaran
        
        Returns:
            Numero de ofertas eliminadas
        """
        if self.pool is None:
            await self.initialize_pool()

        if not portal_name:
            logger.warning("⚠️ Nombre de portal no proporcionado")
            return 0
        
        portal_id = await self.get_portal_id(portal_name)
        if not portal_id:
            logger.warning(f"⚠️ Portal '{portal_name}' no encontrado")
            return 0

        async with self.pool.acquire() as conn:
            deleted_ids = await conn.fetch(
                "DELETE FROM job_offers WHERE portal_id = $1 RETURNING id", 
                portal_id
            )
            deleted_count = len(deleted_ids)
            logger.info(f"✅ Eliminadas {deleted_count} ofertas del portal '{portal_name}'")
            return deleted_count
            

    #get_stats()
    async def get_stats(self) -> Dict:
        """
        Obtiene estadísticas generales de forma ASÍNCRONA

        Returns:
            Diccionario con estadísticas como total de ofertas, ofertas por portal, etc.
        """
        if self.pool is None:
            await self.initialize_pool()

        async with self.pool.acquire() as conn:
            stats = {}

            # Total de ofertas
            total = await conn.fetchval("SELECT COUNT(*) FROM job_offers")
            stats['total_offers'] = total

            # Ofertas por portal
            results = await conn.fetch("""
                SELECT jp.name, COUNT(*) as count
                FROM job_offers jo
                JOIN job_portals jp ON jo.portal_id = jp.id
                GROUP BY jp.name
            """)
            stats['offers_by_portal'] = {row['name']: row['count'] for row in results}
            
            # Top provincias
            provinces = await conn.fetch("""
                SELECT province, COUNT(*) as count
                FROM job_offers
                WHERE province IS NOT NULL
                GROUP BY province
                ORDER BY count DESC
                LIMIT 10
            """)
            stats['top_provinces'] = {row['province']: row['count'] for row in provinces}

            logger.info(f"📊 Estadísticas: {stats['total_offers']} ofertas totales")
            return stats
            

    #get_stats_by_portal()
    async def get_stats_by_portal(self, portal_name: str) -> Dict:
        """
        Obtiene estadísticas específicas para un portal de forma ASÍNCRONA

        Returns:
            Diccionario con estadísticas como total de ofertas, provincias más comunes, etc.
        """
        if self.pool is None:
            await self.initialize_pool()

        portal_id = await self.get_portal_id(portal_name)
        if not portal_id:
            logger.warning(f"⚠️ Portal '{portal_name}' no encontrado")
            return {}

        async with self.pool.acquire() as conn:
            stats = {}

            # Total de ofertas para el portal
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM job_offers WHERE portal_id = $1", 
                portal_id
            )
            stats['total_offers'] = total

            # Provincias más comunes para el portal
            provinces = await conn.fetch("""
                SELECT province, COUNT(*) as count
                FROM job_offers
                WHERE portal_id = $1 AND province IS NOT NULL
                GROUP BY province
                ORDER BY count DESC
                LIMIT 5
            """, portal_id)
            stats['top_provinces'] = {row['province']: row['count'] for row in provinces}

            logger.info(f"📊 Estadísticas para '{portal_name}': {total} ofertas")
            return stats
            

    #testing

    # script de prueba para verificar todas las operaciones
if __name__ == "__main__":
    repo = JobOffersRepository()

    #probar conexion
    repo.test_connection()

    # probar guardado de oferta
    sample_offer = {
        "id": "test123",
        "title": "Desarrollador Python",
        "company": "Tech Company",
        "city": "Madrid",
        "province": "Madrid",
        "salary": "30000-40000 EUR",
        "description": "Buscamos desarrollador Python con experiencia en Django.",
        "url": "https://www.infojobs.net/oferta-desarrollador-python",
        "published_at": "2024-06-01T12:00:00Z"
    }

    repo.save_offer(sample_offer, portal_name="InfoJobs")

    # probar busqueda de oferta
    results = repo.search_offers("Python", portal_name="InfoJobs")
    print(f"Ofertas encontradas: {len(results)}")

    # probar obtencion de oferta por ID
    if results:
        offer_id = results[0]['id']
        offer = repo.get_offer_by_id(offer_id)
        print(f"Oferta obtenida por ID: {offer['title']}")
    
    # probar obtencion de ofertas recientes
    recent_offers = repo.get_recent_offers(limit=5)
    print(f"Ofertas recientes: {len(recent_offers)}")

    # probar eliminacion de ofertas por portal
    deleted_count = repo.delete_offers_by_portal("InfoJobs")
    print(f"Ofertas eliminadas del portal 'InfoJobs': {deleted_count}")

    # probar obtencion de estadisticas generales
    stats = repo.get_stats()
    print(f"Estadísticas generales: {stats}")

    # probar obtencion de estadisticas por portal
    portal_stats = repo.get_stats_by_portal("InfoJobs")
    print(f"Estadísticas para 'InfoJobs': {portal_stats}")

    # probar guardado de ofertas en batch
    batch_offers = [
        {
            "id": "batch1",
            "title": "Desarrollador Frontend",
            "company": "Tech Company",
            "city": "Barcelona",
            "province": "Barcelona",
            "salary": "25000-35000 EUR",
            "description": "Buscamos desarrollador Frontend con experiencia en React.",
            "url": "https://www.infojobs.net/oferta-desarrollador-frontend",
            "published_at": "2024-06-02T10:00:00Z"
        },
        {
            "id": "batch2",
            "title": "Analista de Datos",
            "company": "Data Company",
            "city": "Valencia",
            "province": "Valencia",
            "salary": "28000-38000 EUR",
            "description": "Buscamos analista de datos con experiencia en Python y SQL.",
            "url": "https://www.infojobs.net/oferta-analista-datos",
            "published_at": "2024-06-03T09:00:00Z"
        }
    ]

    saved_count = repo.save_offer_batch(batch_offers, portal_name="InfoJobs")
    print(f"Ofertas guardadas en batch: {saved_count}")
