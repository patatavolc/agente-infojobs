from pydantic import BaseModel, Field
from typing import Optional
from openai import OpenAI
import os

# Definir que infromacion necesitamos extraer de la frase del usuario
class BusquedaInfoJobs(BaseModel):
    query: str = Field(description="El puesto de trabajo o tecnologia (ej:Python, camarero, contable)")
    provincia: Optional[str] = Field(default=None, description="La provincia donde se busca el trabajo (ej: Madrid, Barcelona)")
    teletrabajo: bool = Field(False, description="True si el usuario menciona explicitamente teletrabajo o remoto")
    experiencia_minima: Optional[int] = Field(None, description="Años de experiencia si se menciona")

class AgenteBuscador:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def interpretar_frase(self, frase_usuario: str) -> BusquedaInfoJobs:
        completion = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un experto en el mercado laboral español. Extrae los parámetros de búsqueda para InfoJobs."},
                {"role": "user", "content": frase_usuario},
            ],
            response_format=BusquedaInfoJobs,
        )
        return completion.choices[0].message.parsed