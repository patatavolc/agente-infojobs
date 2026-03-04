"""
Repositorio para gestionar ofertas de empleo en PostgreSQL
Proporciona metodos para guardar, buscar y obtener estadisticas
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from typing import List, Dict, Optional
from datetime import datetime
from config import DatabaseConfig

class JobOffersRepository:
    def __init__(self):
        self.connection_params = DatabaseConfig.get_connection_params()
        print(f"Conectando a la base de datos con parametros: {self.connection_params['database']}@{self.connection_params['host']}:{self.connection_params['port']}")

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
                print(f" Host: {self.connection_params['host']}")
                print(f" Port: {self.connection_params['port']}")
                print(f" Database: {self.connection_params['dbname']}")
                print(f" User: {self.connection_params['user']}")
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
