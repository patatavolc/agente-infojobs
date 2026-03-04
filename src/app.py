from flask import Flask, request, jsonify
from langchain_openai import ChatOpenAI
from src.agent_logic import AgenteBuscador
from src.infojobs_client import InfoJobsClient
from src.db_repository import JobOffersRepository
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
agente = AgenteBuscador()
infojobs = InfoJobsClient()
db_repo = JobOffersRepository()
llm_resumen = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Memoria manual simple: lista de mensajes por usuario
memorias_por_usuarios = {}

def crear_resumen(mensajes):
    """Genera un resumen de los últimos mensajes"""
    if not mensajes:
        return "Sin historial previo"
    
    texto = "\n".join([f"- {m['rol']}: {m['contenido']}" for m in mensajes[-5:]])
    
    prompt = f"""Resume brevemente esta conversación sobre búsqueda de empleo:
    
{texto}

Resumen:"""
    
    response = llm_resumen.invoke(prompt)
    return response.content

@app.route("/buscar", methods=["POST"])
def buscar():
    try:
        data = request.json
        logger.info(f"Nueva consulta recibida: {data}")

        frase_usuario = data.get("consulta")
        user_id = data.get("user_id", "default")
        
        if not frase_usuario:
            return jsonify({"error": "No se proporcionó una consulta"}), 400

        # Crear memoria si no existe
        if user_id not in memorias_por_usuarios:
            memorias_por_usuarios[user_id] = []
            logger.info(f"Memoria creada para usuario: {user_id}")

        memoria_actual = memorias_por_usuarios[user_id]
        
        # Generar resumen del historial
        resumen = crear_resumen(memoria_actual)

        # Interpretar frase con contexto
        parametros = agente.interpretar_frase_con_contexto(frase_usuario, resumen)
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
        
        # Busqueda en InfoJobs
        resultados = infojobs.buscar_ofertas(query=parametros.query, provincia_id=parametros.provincia_id)
        logger.info(f"Resultados obtenidos: {resultados['totalResults']} ofertas encontradas")

        # Guardar ofertas en la base de datos
        ofertas_guardadas = 0
        if resultados.get('items'):
            logger.info(f"Guardando {len(resultados['items'])} ofertas en la base de datos...")

            for oferta in resultados['items']:
                # Adaptar formato del mock a formato esperado por la DB
                oferta_db = {
                    'id': oferta.get('id', f"infojobs_{hash(oferta['title'] + oferta['company'])}"),
                    'title': oferta['title'],
                    'company': oferta['company'],
                    'city': oferta['city'],
                    'province': parametros.provincia if parametros.provincia else 'Sin especificar',
                    'salary': oferta.get('salary', 'No especificado'),
                    'description': f"Búsqueda: {parametros.query}",
                    'url': f"https://www.infojobs.net/oferta/{oferta.get('id', 'desconocido')}",
                    'published_at': oferta.get('published_at')
                }

                try:
                    if db_repo.save_offer(oferta_db, portal_name="InfoJobs"):
                        ofertas_guardadas += 1
                except Exception as e:
                    logger.error(f"Error guardando oferta {oferta_db['id']}: {str(e)}")
            logger.info(f"✅ {ofertas_guardadas}/{len(resultados['items'])} ofertas guardadas en la DB")

        return jsonify({
            "analisis_ia": parametros.model_dump(),
            "resumen_conversacion": resumen,
            "ofertas": resultados,
            "guardadas_en_db": ofertas_guardadas
        })
        
    except Exception as e:
        logger.error(f"Error procesando la consulta: {str(e)}", exc_info=True)
        return jsonify({
            "error": f"Error interno: {str(e)}",
            "tipo": type(e).__name__
        }), 500

@app.route("/estadisticas", methods=["GET"])
def estadisticas():
    """ Endpoint para obtener estadisticas de la base de datos"""
    try:
        stats = db_repo.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

@app.route("/ofertas/recientes", methods=["GET"])
def ofertas_recientes():
    """ Endpoint para obtener ofertas recientes de la BD"""
    try:
        limit = request.args.get('limit', 10, type=int)
        ofertas = db_repo.get_recent_offers(limit=limit)

        # Convertir a formato JSON serializable
        ofertas_json = []
        for oferta in ofertas:
            oferta_dict = dict(oferta)
            # Convertir datetime a string
            if oferta_dict.get('published_at'):
                oferta_dict['published_at'] = oferta_dict['published_at'].isoformat()
            if oferta_dict.get('scraped_at'):
                oferta_dict['scraped_at'] = oferta_dict['scraped_at'].isoformat()
            if oferta_dict.get('updated_at'):
                oferta_dict['updated_at'] = oferta_dict['updated_at'].isoformat()
            ofertas_json.append(oferta_dict)

        return jsonify({
            "total": len(ofertas_json),
            "ofertas": ofertas_json
        })
    except Exception as e:
        logger.error(f"Error obteniendo ofertas recientes: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

@app.route("/ofertas/buscar", methods=["GET"])
def buscar_en_db():
    """ Buscar ofertas guardadas en la db por palabra clave"""
    try:
        keyword = request.args.get('keyword', '')
        if not keyword:
            return jsonify({"error": "Se requiere una palabra clave para buscar"}), 400
        limit = request.args.get('limit', 10, type=int)

        ofertas = db_repo.search_offers(keyword=keyword, limit=limit)

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
        
        return jsonify({
            "keyword": keyword,
            "total": len(ofertas_json),
            "ofertas": ofertas_json
        })
    except Exception as e:
        logger.error(f"Error buscando ofertas en DB: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


if __name__ == "__main__":
    # Verificar conexion a DB al iniciar
    logger.info("Verificando conexion a la base de datos...")
    if db_repo.test_connection():
        logger.info("✅ Conexion a la base de datos exitosa.")
    else:
        logger.error("❌ No se pudo conectar a la base de datos.")
    app.run(debug=True, port=5000)
