from pydantic import BaseModel, Field
from typing import Optional
from openai import OpenAI
from src.constants import PROVINCIAS_INFOJOBS, normalizar_texto
import os

# Definir que infromacion necesitamos extraer de la frase del usuario
class BusquedaInfoJobs(BaseModel):
    query: str = Field(description="El puesto de trabajo o tecnologia (ej:Python, camarero, contable)")
    provincia: Optional[str] = Field(default=None, description="La provincia donde se busca el trabajo (ej: Madrid, Barcelona)")
    provincia_id: Optional[str] = Field(default=None, description="El ID de la provincia segun InfoJobs (ej: 33 para Madrid)")
    teletrabajo: bool = Field(False, description="True si el usuario menciona explicitamente teletrabajo o remoto")
    experiencia_minima: Optional[int] = Field(None, description="Años de experiencia si se menciona")

class AgenteBuscador:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def interpretar_frase(self, frase_usuario: str) -> BusquedaInfoJobs:
        provincias_validas = ", ".join(PROVINCIAS_INFOJOBS.keys())
        completion = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Eres un experto en el mercado laboral español. Extrae los parámetros de búsqueda para InfoJobs. Provincias validas: {provincias_validas}"},
                {"role": "user", "content": frase_usuario},
            ],
            response_format=BusquedaInfoJobs,
        )

        # Extraer el objeto procesado por la IA
        datos = completion.choices[0].message.parsed

        # Logica de mapeo: Convertir el nombre de la provincia en su ID
        if datos.provincia:
            nombre_normalizado = normalizar_texto(datos.provincia)
            datos.provincia_id = PROVINCIAS_INFOJOBS.get(nombre_normalizado)
        return datos

# Bloque de prueba para verificar funcionamiento
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    agente = AgenteBuscador()
    test_frase = "Busco trabajo de Python en Barcelona con teletrabajo"
    resultado = agente.interpretar_frase(test_frase)

    print("--- Resultados del Agente ---")
    print(f"Busqueda: {resultado.query}")
    print(f"Provincia: {resultado.provincia}")
    print(f"Provincia ID: {resultado.provincia_id}")
    print(f"Teletrabajo: {resultado.teletrabajo}")