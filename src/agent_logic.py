from pydantic import BaseModel, Field
from typing import Optional
from langchain_openai import ChatOpenAI
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
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    def interpretar_frase(self, frase_usuario: str, memoria_usuario) -> BusquedaInfoJobs:
        provincias_validas = ", ".join(PROVINCIAS_INFOJOBS.keys())

        resumen_actual = memoria_usuario.buffer

        llm_con_estructura = self.kkm.with_structured_output(BusquedaInfoJobs)

        prompt = f"""
        Eres un experto en el mercado laboral español.
        Contexto de la conversacion previa: {resumen_actual}

        Provincias validas: {provincias_validas}

        Analiza la nueva frase y extrae los parametros actualizados: "{frase_usuario}"
        """

        # 1. La IA razona basandose en el resumen + la frase nueva
        datos = llm_con_estructura.invoke(prompt)

        # 2. Guardamos esta interaccion en la memoria para que el resumen se actualice
        memoria_usuario.save_context({"input": frase_usuario}, {"output": f"Buscando {datos.query} en {datos.provincia} or 'toda España'"})

        # 3. Logica de mapeo de IDs
        if datos.provincia:
            nombre_normalizado = normalizar_texto(datos.provincia)
            datos.provincia_id = PROVINCIAS_INFOJOBS.get(nombre_normalizado)
      
        return datos