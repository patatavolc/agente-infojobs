"""
API principal del agente buscador de empleo
Migrado de Flask a FastAPI para mejor performance y validación
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from langchain_openai import ChatOpenAI
from src.services.agent import AgenteBuscador
from src.clients.factory import ClientFactory
from src.repositories.database import JobOffersRepository
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title="Agente Buscador de Empleo",
    description="API para búsqueda inteligente de ofertas de empleo usando IA",
    version="2.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar componentes
agente = AgenteBuscador()
infojobs_client = ClientFactory.create_infojobs_client()
db_repo = JobOffersRepository()
llm_resumen = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Memoria de conversaciones
memorias_por_usuarios: Dict[str, List[Dict]] = {}


# ==================== MODELOS PYDANTIC ====================

class BuscarRequest(BaseModel):
    """Modelo de petición para búsqueda de ofertas"""
    consulta: str = Field(..., min_length=3, description="Consulta en lenguaje natural")
    user_id: Optional[str] = Field("default", description="ID del usuario")

    class Config:
        json_schema_extra = {
            "example": {
                "consulta": "Desarrollador Python en Madrid",
                "user_id": "usuario123"
            }
        }


class BuscarResponse(BaseModel):
    """Modelo de respuesta para búsqueda"""
    analisis_ia: Dict
    resumen_conversacion: str
    ofertas: Dict
    guardadas_en_db: int
    modo_api: str
    portal: str


class OfertaDB(BaseModel):
    """Modelo de oferta de la base de datos"""
    id: int
    portal_id: int
    external_id: str
    title: str
    company: str
    city: Optional[str]
    province: Optional[str]
    salary: Optional[str]
    description: Optional[str]
    url: Optional[str]
    published_at: Optional[str]
    scraped_at: str
    updated_at: str
    portal_name: str


class EstadisticasResponse(BaseModel):
    """Modelo de respuesta de estadísticas"""
    total_offers: int
    offers_by_portal: Dict[str, int]
    top_provinces: Dict[str, int]


class StatusResponse(BaseModel):
    """Modelo de respuesta del estado del sistema"""
    infojobs_mode: str
    infojobs_portal: str
    database_connected: bool
    available_portals: List[str]


# ==================== FUNCIONES AUXILIARES ====================

def crear_resumen(mensajes: List[Dict]) -> str:
    """Genera un resumen de los últimos mensajes"""
    if not mensajes:
        return "Sin historial previo"
    
    texto = "\n".join([f"- {m['rol']}: {m['contenido']}" for m in mensajes[-5:]])
    
    prompt = f"""Resume brevemente esta conversación sobre búsqueda de empleo:
    
{texto}

Resumen:"""
    
    # Nota: invoke es síncrono aquí, pero es rápido
    # Si queremos hacerlo async, usar: await llm_resumen.ainvoke(prompt)
    response = llm_resumen.invoke(prompt)
    return response.content


# ==================== ENDPOINTS ====================

@app.get("/", tags=["Health"])
async def root():
    """Endpoint raíz - Health check"""
    return {
        "status": "online",
        "service": "Agente Buscador de Empleo",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.post("/buscar", response_model=BuscarResponse, tags=["Búsqueda"])
async def buscar(request: BuscarRequest):
    """
    Busca ofertas de empleo usando lenguaje natural
    
    - **consulta**: Descripción en lenguaje natural (ej: "Python en Barcelona")
    - **user_id**: Identificador del usuario para mantener contexto
    
    Returns ofertas encontradas y las guarda en la base de datos
    """
    try:
        logger.info(f"Nueva consulta recibida: {request.dict()}")

        frase_usuario = request.consulta
        user_id = request.user_id

        # Crear memoria si no existe
        if user_id not in memorias_por_usuarios:
            memorias_por_usuarios[user_id] = []
            logger.info(f"Memoria creada para usuario: {user_id}")

        memoria_actual = memorias_por_usuarios[user_id]
        
        # Generar resumen del historial
        resumen = crear_resumen(memoria_actual)

        # Interpretar frase con contexto
        parametros = await agente.interpretar_frase_con_contexto(frase_usuario, resumen)
        logger.info(f"Parametros extraidos por el agente: {parametros}")   
        
        # Guardar interacción
        memoria_actual.append({"rol": "usuario", "contenido": frase_usuario})
        memoria_actual.append({
            "rol": "asistente", 
            "contenido": f"Búsqueda: {parametros.query} en {parametros.provincia or 'toda España'}"
        })
        
        # Limitar historial a últimos 20 mensajes
        if len(memoria_actual) > 20:
            memoria_actual[:] = memoria_actual[-20:]
        
        # Búsqueda en InfoJobs (ASYNC)
        resultados = await infojobs_client.buscar_ofertas(
            query=parametros.query,
            provincia_id=parametros.provincia_id,
            limit=10
        )
        
        modo = "MOCK" if infojobs_client.is_mock else "REAL"
        logger.info(f"Resultados obtenidos [{modo}]: {resultados['totalResults']} ofertas encontradas")

        # Guardar ofertas en la base de datos
        ofertas_guardadas = 0
        if resultados.get('items'):
            logger.info(f"Guardando {len(resultados['items'])} ofertas en la base de datos...")

            for oferta in resultados['items']:
                oferta_db = {
                    'id': oferta.get('id', f"infojobs_{hash(oferta['title'] + oferta['company'])}"),
                    'title': oferta['title'],
                    'company': oferta['company'],
                    'city': oferta['city'],
                    'province': parametros.provincia if parametros.provincia else 'Sin especificar',
                    'salary': oferta.get('salary', 'No especificado'),
                    'description': oferta.get('description', f"Búsqueda: {parametros.query}"),
                    'url': oferta.get('url', f"https://www.infojobs.net/oferta/{oferta.get('id', 'desconocido')}"),
                    'published_at': oferta.get('published_at')
                }

                try:
                    if await db_repo.save_offer(oferta_db, portal_name="InfoJobs"):
                        ofertas_guardadas += 1
                except Exception as e:
                    logger.error(f"Error guardando oferta {oferta_db['id']}: {str(e)}")
            
            logger.info(f"✅ {ofertas_guardadas}/{len(resultados['items'])} ofertas guardadas en la DB")

        return BuscarResponse(
            analisis_ia=parametros.model_dump(),
            resumen_conversacion=resumen,
            ofertas=resultados,
            guardadas_en_db=ofertas_guardadas,
            modo_api=modo,
            portal=infojobs_client.get_portal_name()
        )
        
    except Exception as e:
        logger.error(f"Error procesando la consulta: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Error interno: {str(e)}",
                "tipo": type(e).__name__
            }
        )


@app.get("/estadisticas", response_model=EstadisticasResponse, tags=["Estadísticas"])
async def estadisticas():
    """
    Obtiene estadísticas generales de la base de datos
    
    Returns:
    - Total de ofertas
    - Ofertas por portal
    - Top 10 provincias con más ofertas
    """
    try:
        stats = await db_repo.get_stats()
        return EstadisticasResponse(**stats)
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.get("/ofertas/recientes", tags=["Ofertas"])
async def ofertas_recientes(
    limit: int = Query(10, ge=1, le=100, description="Número de ofertas a obtener")
):
    """
    Obtiene las ofertas más recientes de la base de datos
    
    - **limit**: Número máximo de ofertas (1-100)
    """
    try:
        ofertas = await db_repo.get_recent_offers(limit=limit)

        ofertas_json = []
        for oferta in ofertas:
            oferta_dict = dict(oferta)
            if oferta_dict.get('published_at'):
                oferta_dict['published_at'] = oferta_dict['published_at'].isoformat()
            if oferta_dict.get('scraped_at'):
                oferta_dict['scraped_at'] = oferta_dict['scraped_at'].isoformat()
            if oferta_dict.get('updated_at'):
                oferta_dict['updated_at'] = oferta_dict['updated_at'].isoformat()
            ofertas_json.append(oferta_dict)

        return {
            "total": len(ofertas_json),
            "ofertas": ofertas_json
        }
    except Exception as e:
        logger.error(f"Error obteniendo ofertas recientes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.get("/ofertas/buscar", tags=["Ofertas"])
async def buscar_en_db(
    keyword: str = Query(..., min_length=2, description="Palabra clave para buscar"),
    limit: int = Query(10, ge=1, le=100, description="Número máximo de resultados")
):
    """
    Busca ofertas guardadas en la base de datos por palabra clave
    
    - **keyword**: Palabra clave a buscar en título, empresa o descripción
    - **limit**: Número máximo de resultados (1-100)
    """
    try:
        ofertas = await db_repo.search_offers(keyword=keyword, limit=limit)

        ofertas_json = []
        for oferta in ofertas:
            oferta_dict = dict(oferta)
            if oferta_dict.get('published_at'):
                oferta_dict['published_at'] = oferta_dict['published_at'].isoformat()
            if oferta_dict.get('scraped_at'):
                oferta_dict['scraped_at'] = oferta_dict['scraped_at'].isoformat()
            if oferta_dict.get('updated_at'):
                oferta_dict['updated_at'] = oferta_dict['updated_at'].isoformat()
            ofertas_json.append(oferta_dict)
        
        return {
            "keyword": keyword,
            "total": len(ofertas_json),
            "ofertas": ofertas_json
        }
    except Exception as e:
        logger.error(f"Error buscando ofertas en DB: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.get("/api/status", response_model=StatusResponse, tags=["Health"])
async def api_status():
    """
    Verifica el estado de las APIs y servicios
    
    Returns información sobre:
    - Modo de InfoJobs (MOCK/REAL)
    - Estado de conexión a base de datos
    - Portales disponibles
    """
    return StatusResponse(
        infojobs_mode="MOCK" if infojobs_client.is_mock else "REAL",
        infojobs_portal=infojobs_client.get_portal_name(),
        database_connected=await db_repo.test_connection(),
        available_portals=ClientFactory.get_available_portals()
    )


# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup_event():
    """Se ejecuta al iniciar el servidor"""
    logger.info("🚀 Iniciando Agente Buscador de Empleo API v2.0 (ASYNC)")
    
    # Inicializar pool de base de datos
    logger.info("Inicializando pool de conexiones a la base de datos...")
    await db_repo.initialize_pool()
    
    # Verificar conexión a DB
    logger.info("Verificando conexión a la base de datos...")
    if await db_repo.test_connection():
        logger.info("✅ Conexión a la base de datos exitosa.")
    else:
        logger.error("❌ No se pudo conectar a la base de datos.")
    
    # Mostrar modo de API
    modo_api = "MOCK" if infojobs_client.is_mock else "REAL"
    logger.info(f"🔌 InfoJobs Client Mode: {modo_api}")
    logger.info("📖 Documentación disponible en: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Se ejecuta al cerrar el servidor"""
    logger.info("🛑 Cerrando Agente Buscador de Empleo API")
    
    # Cerrar clientes HTTP
    logger.info("🔒 Cerrando clientes HTTP...")
    await ClientFactory.close_all_clients()
    
    # Cerrar pool de base de datos
    if db_repo.pool:
        logger.info("🔒 Cerrando pool de base de datos...")
        await db_repo.pool.close()
    
    logger.info("✅ Cierre limpio completado")


# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Hot reload en desarrollo
        log_level="info"
    )
