"""
Configuracion centralizada del proyecto
Carga variables de entorno y proporciona acceso a configuraciones
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Determinar la ruta base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / '.env'

# Cargar las variables de entorno
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    print(f"Cargado archivo de configuración: {ENV_FILE}")
else:
    print(f"Archivo de configuración no encontrado: {ENV_FILE}")
    print(" Copia .env.example a .env y configura tus variables de entorno.")

# Configuracion de la base de datos
class DatabaseConfig:
    """Configuracion de conexion a PostgreSQL"""

    HOST = os.getenv('DB_HOST', 'localhost')
    PORT = os.getenv('DB_PORT', '5432')
    NAME = os.getenv('DB_NAME', 'jobsdb')
    USER = os.getenv('DB_USER', 'postgres')
    PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

    @classmethod
    def get_connection_string(cls) -> str:
        """Devuelve la cadena de conexion para psycopg2"""
        return f"host={cls.HOST} port={cls.PORT} dbname={cls.NAME} user={cls.USER} password={cls.PASSWORD}"
    @classmethod
    def get_connection_params(cls) -> dict:
        """Devuelve un diccionario con los parametros de conexion para psycopg2"""
        return {
            'host': cls.HOST,
            'port': cls.PORT,
            'dbname': cls.NAME,
            'user': cls.USER,
            'password': cls.PASSWORD
        }

    @classmethod
    def get_dsn(cls) -> str:
        """Devuelve el DSN para conexiones URI"""
        return f"postgresql://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.NAME}"