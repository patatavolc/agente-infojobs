from flask import Flask, request, jsonify
from src.agent_logic import AgenteBuscador
from src.infojobs_client import InfoJobsClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
agente = AgenteBuscador()
infojobs = InfoJobsClient()

@app.route("/buscar", methods=["POST"])
def buscar():
    data = request.json
    frase_usuario = data.get("consulta")
    
    if not frase_usuario:
        return jsonify({"error": "No se proporcionó una consulta"}), 400

    # 1. El Agente interpreta la frase y nos da los parámetros limpios e IDs
    parametros = agente.interpretar_frase(frase_usuario)
    
    # 2. El Cliente (simulado por ahora) busca las ofertas
    # Usamos los parámetros que extrajo la IA
    resultados = infojobs.buscar_ofertas(
        query=parametros.query,
        provincia_id=parametros.provincia_id
    )

    # 3. Respondemos al usuario con los datos y lo que la IA entendió
    return jsonify({
        "analisis_ia": {
            "puesto": parametros.query,
            "provincia": parametros.provincia,
            "remoto": parametros.teletrabajo
        },
        "ofertas": resultados
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)