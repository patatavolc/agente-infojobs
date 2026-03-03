from flask import Flask, request, jsonify
from langchain_community.memory import ConversationSummaryMemory
from langchain_openai import ChatOpenAI
from src.agent_logic import AgenteBuscador
from src.infojobs_client import InfoJobsClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
agente = AgenteBuscador()
infojobs = InfoJobsClient()

# Modelo especifico para que la memoria genere los resumenes
llm_resumen = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Diccionario, aqui se guardan las memorias por separado
# Clave: user_id | Valor: instancia de ConversationSummaryMemory
memorias_por_usuarios = {}

@app.route("/buscar", methods=["POST"])
def buscar():
    data = request.json
    frase_usuario = data.get("consulta")
    # Si no nos pasan el user_id, usamos 'default' (para pruebas)
    user_id = data.get("user_id", "default")
    
    if not frase_usuario:
        return jsonify({"error": "No se proporcionó una consulta"}), 400

    # 1. Recuperar o crear la memoria para ESTE usuario
    if user_id not in memorias_por_usuarios:
        memorias_por_usuarios[user_id] = ConversationSummaryMemory(llm=llm_resumen)

    memoria_actual = memorias_por_usuarios[user_id]

    # 2. El agente interpretaq la frase usando SU memoria
    parametros = agente.interpretar_frase(frase_usuario, memoria_actual)   
    
    # 3. Busqueda (mock o real)
    resultados = infojobs.buscar_ofertas(query=parametros.query, provincia_id=parametros.provincia_id)

    return jsonify({
        "analisis_ia": parametros.dict(),
        "resumen_actual": memoria_actual.buffer,
        "ofertas": resultados
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
