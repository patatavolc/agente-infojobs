from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from src.constants import PROVINCIAS_INFOJOBS, normalizar_texto
import os

class BusquedaInfoJobs(BaseModel):
    query: str = Field(description="Palabra clave principal para la búsqueda (ej: 'python', 'ingeniero')")
    provincia: str = Field(default=None, description="Nombre de la provincia española donde buscar")
    provincia_id: str = Field(default=None, description="ID numérico de la provincia según InfoJobs")
    teletrabajo: bool = Field(default=False, description="Si el usuario busca explícitamente teletrabajo")

class AgenteBuscador:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY no está configurada en .env")
        
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    def interpretar_frase_con_contexto(self, frase_usuario: str, resumen_contexto: str) -> BusquedaInfoJobs:
        provincias_validas = ", ".join(PROVINCIAS_INFOJOBS.keys())

        llm_con_estructura = self.llm.with_structured_output(BusquedaInfoJobs)

        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres un asistente que interpreta consultas de búsqueda de empleo en InfoJobs.

Provincias disponibles: {provincias_validas}

Contexto de conversación previa:
{resumen_contexto}

Extrae:
1. query: Palabra clave del trabajo (ej: "python", "enfermero")
2. provincia: Nombre de la provincia si se menciona
3. provincia_id: Déjalo en None, lo calcularé yo
4. teletrabajo: true solo si se menciona explícitamente

Si el usuario dice cosas como "ahora en Barcelona" o "mejor en Madrid", 
usa el contexto previo para mantener la query anterior."""),
            ("user", "{input}")
        ])

        cadena = prompt | llm_con_estructura
        resultado = cadena.invoke({"input": frase_usuario})

        # Normalizar provincia
        if resultado.provincia:
            prov_norm = normalizar_texto(resultado.provincia)
            resultado.provincia_id = PROVINCIAS_INFOJOBS.get(prov_norm)
            if not resultado.provincia_id:
                print(f"⚠️  Provincia '{resultado.provincia}' no reconocida")

        return resultado