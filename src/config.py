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
    
# Configuracion e INFOJOBS
class InfoJobsConfig:
    """Configuracion para la API de InfoJobs"""

    CLIENT_ID = os.getenv('INFOJOBS_CLIENT_ID', '')
    CLIENT_SECRET = os.getenv('INFOJOBS_CLIENT_SECRET', '')
    BASE_URL = os.getenv('INFOJOBS_BASE_URL', 'https://api.infojobs.net/api/9/')

    @classmethod
    def is_configured(cls) -> bool:
        """Verifica si las credenciales de InfoJobs estan configuradas"""
        return bool(cls.CLIENT_ID and cls.CLIENT_SECRET)
    
# Configuracion de Jooble
class JoobleConfig:
    """Configuracion para la API de Jooble"""

    API_KEY = os.getenv('JOOBLE_API_KEY', '')
    BASE_URL = os.getenv('JOOBLE_BASE_URL', 'https://jooble.org/api/')

    @classmethod
    def is_configured(cls) -> bool:
        """Verifica si la clave de API de Jooble esta configurada"""
        return bool(cls.API_KEY)
    
# Configuracion de Adzuna
class AdzunaConfig:
    """Configuracion para la API de Adzuna"""

    APP_ID = os.getenv('ADZUNA_APP_ID', '')
    APP_KEY = os.getenv('ADZUNA_APP_KEY', '')
    BASE_URL = os.getenv('ADZUNA_BASE_URL', 'https://api.adzuna.com/v1/api/')

    @classmethod
    def is_configured(cls) -> bool:
        """Verifica si las credenciales de Adzuna estan configuradas"""
        return bool(cls.APP_ID and cls.APP_KEY)
    

# Configuracion general de la aplicacion
class AppConfig:
    """Configuracion general de la aplicacion"""

    DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    ENVIROMENT = os.getenv('ENVIRONMENT', 'development')

    # Directorios del proyecto
    BASE_DIR = BASE_DIR
    SRC_DIR = BASE_DIR / 'src'
    DB_DIR = BASE_DIR / 'db'
    LOGS_DIR = BASE_DIR / 'logs'

    @classmethod
    def create_directories(cls):
        """Crea los directorios necesarios si no existen"""
        cls.LOGS_DIR.mkdir(exist_ok=True)
        print(f"Directorios verificados: logs/")


# Validacion de configuracion
def validate_config(verbose: bool = True) -> dict:
    """
    Valida que todas las configuraciones necesarias esten presentes

    Args: verbose: Si es true, imprime los resultados de validacion

    Returns: Diccionario con el estado de cada configuracion
    """

    status = {
        'database': True,
        'infojobs': InfoJobsConfig.is_configured(),
        'jooble': JoobleConfig.is_configured(),
        'adzuna': AdzunaConfig.is_configured()
    }

    if verbose:
        print("\n" + "=" * 60)
        print("Validacion de Configuracion")
        print("=" * 60)

        # Base de datos
        print(f"{'✅' if status['databse'] else '❌'} Base de Datos: {DatabaseConfig.NAME}@{DatabaseConfig.HOST}")

        # InfoJobs
        if status['infojobs']:
            print(f"✅ InfoJobs: Configurado")
        else:
            print(f"❌ InfoJobs: No configurado. Requiere CLIENT_ID y CLIENT_SECRET (usando modo simulado)")
        
        # Jooble
        if status['jooble']:
            print(f"✅ Jooble: Configurado")
        else:
            print(f" Jooble API: No configurada")
        
        # Adzuna
        if status['adzuna']:
            print(f"✅ Adzuna: Configurado")
        else:
            print(f"Adzuna API: No configurada")
        
        print("=" * 60 + "\n")    
    
    return status
    