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
            logger.info(f"{ofertas_guardadas} /{len(resultados['items'])} ofertas guardadas en la DB")

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

if __name__ == "__main__":
    app.run(debug=True, port=5000)
