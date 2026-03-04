"""
Repositorio para gestionar ofertas de empleo en PostgreSQL
Proporciona metodos para guardar, buscar y obtener estadisticas
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from typing import List, Dict, Optional
from datetime import datetime
from src.config import DatabaseConfig

class JobOffersRepository:
    def __init__(self):
        self.connection_params = DatabaseConfig.get_connection_params()
        print(f"Conectando a la base de datos con parametros: {self.connection_params['dbname']}@{self.connection_params['host']}:{self.connection_params['port']}")

    def get_connection(self):
        """ 
        Establece una conexion a la base de datos

        Returns:
            Conexion psycopg2

        Raises: 
            psycopg2.OperationalError: Si no se puede conectar a la base de datos
        """

        try:
            return psycopg2.connect(**self.connection_params)
        except psycopg2.OperationalError as e:
            print(f"❌ Error al conectar a la base de datos: {e}")
            print(f"   Host: {self.connection_params['host']}")
            print(f"   Port: {self.connection_params['port']}")
            print(f"   Database: {self.connection_params['dbname']}")
            print(f"   User: {self.connection_params['user']}")
            raise
    
    def test_connection(self) -> bool:
        """"
        Prueba la conexion a la base de datos

        Returns:
            True si la conexion es exitosa, False en caso contrario
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version();")
                    version = cur.fetchone()
                    print(f"✅ Conexion exitosa a PostgreSQL: {version[0]}")

                    # Verificar que las tablas existen
                    cur.execute("""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                        ORDER BY table_name;
                    """)

                    tables = [row[0] for row in cur.fetchall()]

                    required_tables = ['job_offers', 'job_portals']
                    missing_tables = [t for t in required_tables if t not in tables]

                    if missing_tables:
                        print(f"⚠️ Tablas faltantes en la base de datos: {', '.join(missing_tables)}")
                        return False

                    print(f"✅ Tablas requeridas encontradas: {', '.join(required_tables)}")
                    return True
        except Exception as e:
            print(f"❌ Error al probar la conexion a la base de datos: {e}")
            return False

    def get_portal_id(self, portal_name: str) -> Optional[int]:
        """
        Obtiene el ID del portal por nombre

        Args:
            portal_name: Nombre del portal (ej: 'InfoJobs)
            
        Returns:
            ID del portal o None si no existe
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM job_portals WHERE name = %s", (portal_name,))
                result = cur.fetchone()
                return result[0] if result else None

    def get_or_create_portal(self, portal_name: str, base_url: str = None) -> int:
        """
        Obtiene o crea un portal y devuelve su ID
        
        Args:
            portal_name: Nombre del portal, sino es proporcionado se usara 'Desconocido'
            base_url: URL base del portal, opcional
            
        Returns:
            ID del portal en la base de datos
        """
        portal_id = self.get_portal_id(portal_name)
        if portal_id:
            return portal_id
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO job_portals (name, base_url) VALUES (%s, %s) RETURNING id",
                    (portal_name, base_url)
                )
                portal_id = cur.fetchone()[0]
                conn.commit()
                print(f"✅ Portal '{portal_name}' creado con ID {portal_id}")
                return portal_id
    
    def save_offer(self, offer: Dict, portal_name: str = "InfoJobs") -> bool:
        """
        Guarda una oferta en la base de datos
    
        Args:
            offer: Diccionario con los datos de la oferta
            portal_name: Nombre del portal de origen
            
        Returns:
            True si se guardó exitosamente, False en caso contrario
        """
        portal_id = self.get_portal_id(portal_name)
        if not portal_id:
            portal_id = self.get_or_create_portal(portal_name)

        with self.get_connection() as conn:
            with conn.cursor() as cur:
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

                    cur.execute("""
                        INSERT INTO job_offers
                        (portal_id, external_id, title, company, city, province, salary, 
                        description, url, published_at, raw_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    """, (
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
                        Json(offer)  # Guardar JSON completo
                    ))
                    
                    offer_id = cur.fetchone()[0]
                    conn.commit()
                    print(f"✅ Oferta '{offer.get('title')}' guardada con ID {offer_id}")
                    return True
                    
                except Exception as e:
                    conn.rollback()
                    print(f"❌ Error guardando oferta: {e}")
                    return False

    def save_offer_batch(self, offers: List[Dict], portal_name: str) -> int:
        """
        Guarda multiples ofertas.
        
        Args:
            offers: Lista de diccionarios con los datos de las ofertas
            portal_name: Nombre del portal de origen
        
        Returns:
            Numero de ofertas guardadas exitosamente
        """
        portal_id = self.get_portal_id(portal_name)
        if not portal_id:
            portal_id = self.get_or_create_portal(portal_name)
        
        saved_count = 0
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for offer in offers:
                    try:
                        if self.save_offer(offer, portal_name):
                            saved_count += 1
                    except Exception as e:
                        print(f"❌ Error guardando oferta en batch: {e}")
                        continue
        print(f"✅ Batch guardado: {saved_count}/{len(offers)} ofertas guardadas exitosamente")
        return saved_count

    # search_offer()
    def search_offers(self, keyword: str, portal_name: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        Busca ofertas por palabra clave y opcionalmente por portal
        
        Args:
            keyword: Palabra clave a buscar en título, empresa o descripción
            portal_name: Nombre del portal para filtrar (opcional)
            limit: Número máximo de resultados (default: 100)

        Returns:
            Lista de ofertas que coinciden con la búsqueda
        """

        if portal_name:
            portal_id = self.get_portal_id(portal_name)
            if not portal_id:
                print(f"⚠️ Portal '{portal_name}' no encontrado. Realizando búsqueda sin filtro de portal.")
                portal_id = None
        else:
            portal_id = None
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT jo.*, jp.name AS portal_name
                    FROM job_offers jo
                    JOIN job_portals jp ON jo.portal_id = jp.id
                    WHERE (jo.title ILIKE %s OR jo.company ILIKE %s OR jo.description ILIKE %s)
                """
                params = [f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"]
                
                if portal_id:
                    query += " AND jo.portal_id = %s"
                    params.append(portal_id)
                
                query += " ORDER BY jo.published_at DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, tuple(params))
                results = cur.fetchall()
                print(f"🔍 Búsqueda completada: {len(results)} ofertas encontradas para '{keyword}'")
                return results
        
    #get_offer_by_id()
    def get_offer_by_id(self, offer_id: int) -> Optional[Dict]:
        """
        Obtiene una oferta por su ID
        
        Args:
            offer_id: ID de la oferta en la base de datos
        
        Returns:
            Diccionario con los datos de la oferta o None si no se encuentra
        """

        if not isinstance(offer_id, int):
            print(f"⚠️ ID de oferta inválido: {offer_id}. Debe ser un entero.")
            return None

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT jo.*, jp.name AS portal_name
                    FROM job_offers jo
                    JOIN job_portals jp ON jo.portal_id = jp.id
                    WHERE jo.id = %s
                """, (offer_id,))
                offer = cur.fetchone()
                if offer:
                    print(f"✅ Oferta encontrada: ID {offer_id} - {offer['title']}")
                else:
                    print(f"⚠️ Oferta con ID {offer_id} no encontrada.")
            return offer
        

    #get_recent_offers()
    def get_recent_offers(self, limit: int = 10) -> List[Dict]:
        """
        Obtiene las ofertas mas recientes

        Args:
            limit: Numero maximo de ofertas a obtener (default: 10)
        
        Returns:
            Lista de ofertas ordenadas por fecha de publicacion descendente
        """

        if not isinstance(limit, int) or limit <= 0:
            print(f"⚠️ Limite inválido: {limit}. Debe ser un entero positivo.")
            return []

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT jo.*, jp.name AS portal_name
                    FROM job_offers jo
                    JOIN job_portals jp ON jo.portal_id = jp.id
                    ORDER BY jo.published_at DESC
                    LIMIT %s
                """, (limit,))
                offers = cur.fetchall()
                print(f"✅ {len(offers)} ofertas recientes obtenidas.")
                return offers


    #delete_stats_by_portal()
    def delete_offers_by_portal(self, portal_name: str) -> int:
        """
        Elimina todas las ofertas asociadas a un portal especifico

        Args:
            portal_name: Nombre del portal cuyas ofertas se eliminaran
        
        Returns:
            Numero de ofertas eliminadas
        """

        if not portal_name:
            print("⚠️ Nombre de portal no proporcionado para eliminación.")
            return 0
        
        portal_id = self.get_portal_id(portal_name)
        if not portal_id:
            print(f"⚠️ Portal '{portal_name}' no encontrado. No se eliminarán ofertas.")
            return 0

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM job_offers WHERE portal_id = %s RETURNING id", (portal_id,))
                deleted_offers = cur.fetchall()
                conn.commit()
                deleted_count = len(deleted_offers)
                print(f"✅ Eliminadas {deleted_count} ofertas del portal '{portal_name}'.")
                return deleted_count
            

    #get_stats()
    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas generales de las ofertas de empleo

        Returns:
            Diccionario con estadísticas como total de ofertas, ofertas por portal, etc.
        """

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                stats = {}

                # Total de ofertas
                cur.execute("SELECT COUNT(*) FROM job_offers")
                stats['total_offers'] = cur.fetchone()[0]

                # Ofertas por portal
                cur.execute("""
                    SELECT jp.name, COUNT(*)
                    FROM job_offers jo
                    JOIN job_portals jp ON jo.portal_id = jp.id
                    GROUP BY jp.name
                """)
                stats['offers_by_portal'] = {row[0]: row[1] for row in cur.fetchall()}

                print(f"📊 Estadísticas obtenidas: {stats}")
                return stats
            

    #get_stats_by_portal()
    def get_stats_by_portal(self, portal_name: str) -> Dict:
        """
            Obtiene estadísticas específicas para un portal de empleo

            Returns:
                Diccionario con estadísticas como total de ofertas, provincias más comunes, etc.
        """

        portal_id = self.get_portal_id(portal_name)
        if not portal_id:
            print(f"⚠️ Portal '{portal_name}' no encontrado. No se pueden obtener estadísticas.")
            return {}

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                stats = {}

                # Total de ofertas para el portal
                cur.execute("SELECT COUNT(*) FROM job_offers WHERE portal_id = %s", (portal_id,))
                stats['total_offers'] = cur.fetchone()[0]

                # Provincias más comunes para el portal
                cur.execute("""
                    SELECT province, COUNT(*)
                    FROM job_offers
                    WHERE portal_id = %s AND province IS NOT NULL
                    GROUP BY province
                    ORDER BY COUNT(*) DESC
                    LIMIT 5
                """, (portal_id,))
                stats['top_provinces'] = {row[0]: row[1] for row in cur.fetchall()}

                print(f"📊 Estadísticas para portal '{portal_name}': {stats}")
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
