# Agente de IA para InfoJobs

Agente conversacional inteligente con memoria contextual que interpreta consultas en lenguaje natural y busca ofertas de empleo en InfoJobs.

## Tabla de Contenidos

- [Características](#características)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [API Endpoints](#api-endpoints)
- [Ejemplos](#ejemplos)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Tecnologías Utilizadas](#tecnologías-utilizadas)
- [Resolución de Problemas](#resolución-de-problemas)
- [Capacidades del Agente](#capacidades-del-agente)
- [Seguridad](#seguridad)
- [Provincias Soportadas](#provincias-soportadas)
- [Licencia](#licencia)

---

## Características

- **Inteligencia Artificial**: Usa GPT-4o-mini para interpretar consultas en lenguaje natural
- **Memoria Conversacional**: Mantiene contexto por usuario con resúmenes automáticos
- **Normalización Inteligente**: Reconoce y normaliza todas las provincias de España
- **Structured Output**: Extracción estructurada de parámetros con Pydantic
- **Logging Completo**: Trazabilidad de todas las operaciones
- **Manejo de Errores**: Sistema robusto de gestión de excepciones
- **Mock de API**: Sistema simulado para testing sin dependencias externas

---

## Arquitectura

```
┌─────────────┐
│   Cliente   │ (Insomnia, curl, frontend)
└──────┬──────┘
       │ HTTP POST
       ▼
┌─────────────────────────────────────┐
│         Flask Server (app.py)        │
│  - Gestión de memoria por usuario   │
│  - Generación de resúmenes          │
└──────┬──────────────┬───────────────┘
       │              │
       ▼              ▼
┌─────────────┐  ┌──────────────────┐
│ AgenteBuscador│  │ InfoJobsClient   │
│(agent_logic.py)│  │(infojobs_client)│
│               │  │                  │
│ • GPT-4o-mini │  │ • Mock API       │
│ • Structured  │  │ • Simulación de  │
│   Output      │  │   búsquedas      │
└───────┬───────┘  └──────────────────┘
        │
        ▼
┌─────────────────┐
│   constants.py  │
│ • PROVINCIAS    │
│ • Normalización │
└─────────────────┘
```

### Flujo de Trabajo

1. **Cliente** envía consulta en lenguaje natural
2. **Flask** recupera/crea memoria del usuario
3. **Flask** genera resumen del historial conversacional
4. **AgenteBuscador** interpreta la consulta usando GPT-4o-mini y contexto
5. **AgenteBuscador** normaliza la provincia y extrae parámetros estructurados
6. **InfoJobsClient** busca ofertas (actualmente mock)
7. **Flask** guarda la interacción en memoria
8. **Cliente** recibe resultados + análisis + resumen conversacional

---

## Requisitos

- **Python**: 3.11+
- **Conda**: Para gestión del entorno virtual
- **OpenAI API Key**: Para GPT-4o-mini

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/agente-infojobs.git
cd agente-infojobs
```

### 2. Crear entorno virtual con Conda

```bash
conda env create -f environment.yml
conda activate infojobs_agent
```

### 3. Instalar dependencias adicionales

```bash
pip install langchain sniffio
```

---

## Configuración

### 1. Crear archivo `.env`

```bash
cp .env.example .env
```

### 2. Configurar variables de entorno

Edita `.env` y añade tu API Key de OpenAI:

```env
# OpenAI (OBLIGATORIO)
OPENAI_API_KEY=sk-proj-TU_API_KEY_AQUI

# InfoJobs (OPCIONAL - para cuando la API esté disponible)
INFOJOBS_CLIENT_ID=
INFOJOBS_CLIENT_SECRET=
```

### 3. Obtener API Key de OpenAI

1. Ve a [OpenAI Platform](https://platform.openai.com/api-keys)
2. Crea una nueva API key
3. Cópiala al archivo `.env`

**IMPORTANTE**: Nunca subas el archivo `.env` a Git. Ya está incluido en `.gitignore`.

---

## Uso

### Iniciar el servidor

```bash
# Desde la raíz del proyecto
conda activate infojobs_agent
python -m src.app
```

El servidor estará disponible en `http://localhost:5000`

### Detener el servidor

Presiona `Ctrl+C` en la terminal donde se ejecuta Flask

---

## API Endpoints

### `POST /buscar`

Busca ofertas de empleo interpretando lenguaje natural.

**Request:**

```json
{
  "consulta": "Busco trabajo de desarrollador Python en Madrid",
  "user_id": "usuario123" // Opcional, default: "default"
}
```

**Response:**

```json
{
  "analisis_ia": {
    "query": "python",
    "provincia": "Madrid",
    "provincia_id": "33",
    "teletrabajo": false
  },
  "resumen_conversacion": "El usuario está buscando trabajos de Python en Madrid.",
  "ofertas": {
    "totalResults": 5,
    "currentResults": 3,
    "items": [
      {
        "id": "1001",
        "title": "Desarrollador Python",
        "company": "Tech Solutions S.L.",
        "city": "Madrid",
        "province": { "value": "33" },
        "salary": "30.000€ - 35.000€",
        "contractType": "indefinido"
      }
    ]
  }
}
```

**Parámetros:**

| Campo      | Tipo   | Requerido | Descripción                                       |
| ---------- | ------ | --------- | ------------------------------------------------- |
| `consulta` | string | Sí        | Consulta en lenguaje natural (máx 500 chars)      |
| `user_id`  | string | No        | Identificador del usuario para memoria contextual |

**Códigos de respuesta:**

- `200`: Búsqueda exitosa
- `400`: Error en parámetros de entrada
- `500`: Error interno del servidor

---

## Ejemplos

### 1. Búsqueda simple

```bash
curl -X POST http://localhost:5000/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "consulta": "Desarrollador Python en Madrid"
  }'
```

### 2. Búsqueda con teletrabajo

```bash
curl -X POST http://localhost:5000/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "consulta": "Ingeniero Java remoto o teletrabajo"
  }'
```

### 3. Búsqueda sin provincia específica

```bash
curl -X POST http://localhost:5000/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "consulta": "Analista de datos con SQL"
  }'
```

### 4. Contexto conversacional

**Primera consulta:**

```bash
curl -X POST http://localhost:5000/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "consulta": "Busco trabajos de Python",
    "user_id": "usuario1"
  }'
```

**Segunda consulta (recuerda Python):**

```bash
curl -X POST http://localhost:5000/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "consulta": "Ahora en Barcelona",
    "user_id": "usuario1"
  }'
```

### 5. Usando Insomnia/Postman

**Método**: POST  
**URL**: `http://localhost:5000/buscar`  
**Headers**:

```
Content-Type: application/json
```

**Body**:

```json
{
  "consulta": "Enfermero en Sevilla"
}
```

---

## Estructura del Proyecto

```
agente-infojobs/
│
├── src/
│   ├── app.py              # Servidor Flask principal
│   ├── agent_logic.py      # Lógica del agente IA
│   ├── infojobs_client.py  # Cliente API de InfoJobs (mock)
│   ├── constants.py        # Constantes y mapeo de provincias
│   └── __pycache__/        # Cache de Python
│
├── environment.yml         # Dependencias de Conda
├── .env                    # Variables de entorno (NO SUBIR A GIT)
├── .env.example            # Ejemplo de configuración
├── .gitignore              # Archivos ignorados por Git
├── LICENSE                 # Licencia del proyecto
└── README.md               # Este archivo
```

### Descripción de Archivos Clave

#### `src/app.py`

Servidor Flask que:

- Maneja endpoints HTTP
- Gestiona memoria conversacional por usuario
- Genera resúmenes automáticos con GPT-4o-mini
- Coordina AgenteBuscador e InfoJobsClient
- Implementa logging y manejo de errores

#### `src/agent_logic.py`

Contiene:

- `BusquedaInfoJobs`: Modelo Pydantic para structured output
- `AgenteBuscador`: Clase que interpreta consultas con GPT-4o-mini
- Lógica de normalización de provincias
- Integración con LangChain

#### `src/infojobs_client.py`

Mock de la API de InfoJobs:

- Simula búsquedas de ofertas
- Devuelve datos realistas para testing
- Preparado para reemplazar con API real

#### `src/constants.py`

Define:

- `PROVINCIAS_INFOJOBS`: Mapeo completo de provincias españolas a IDs
- `normalizar_texto()`: Función para normalizar strings con acentos

---

## Tecnologías Utilizadas

| Tecnología        | Versión | Propósito            |
| ----------------- | ------- | -------------------- |
| **Python**        | 3.11    | Lenguaje principal   |
| **Flask**         | Latest  | Framework web        |
| **LangChain**     | 0.3+    | Orquestación de LLM  |
| **OpenAI**        | Latest  | GPT-4o-mini para NLP |
| **Pydantic**      | Latest  | Validación de datos  |
| **Conda**         | Latest  | Gestión de entornos  |
| **python-dotenv** | Latest  | Variables de entorno |

### Dependencias Principales

```yaml
- flask
- flask-cors
- langchain
- langchain-core
- langchain-openai
- langchain-community
- openai
- pydantic
- requests
- python-dotenv
```

---

## Resolución de Problemas

### Error: `ModuleNotFoundError: No module named 'src'`

**Solución:**

```bash
# Usar -m para ejecutar como módulo
python -m src.app

# O añadir al PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python src/app.py
```

### Error: `ModuleNotFoundError: No module named 'sniffio'`

**Solución:**

```bash
pip install sniffio
```

### Error: `openai.AuthenticationError`

**Causa:** API key inválida o no configurada

**Solución:**

1. Verifica que `.env` existe y contiene `OPENAI_API_KEY`
2. Verifica que la key es válida en [OpenAI Platform](https://platform.openai.com/api-keys)
3. Reinicia el servidor después de cambiar `.env`

### Error: Provincia no reconocida

**Logs mostrarán:** `Provincia 'XYZ' no reconocida`

**Solución:** Usa nombres de provincias españolas estándar. Ver lista completa en [`src/constants.py`](src/constants.py)

### Puerto 5000 ocupado

**Solución:**

```bash
# Cambiar puerto en src/app.py
app.run(debug=True, port=5001)
```

### Dependencias corruptas

**Solución:** Recrear entorno

```bash
conda deactivate
conda env remove -n infojobs_agent
conda env create -f environment.yml
conda activate infojobs_agent
pip install langchain sniffio
```

---

## Logs y Debugging

Los logs se muestran en la terminal donde corre Flask:

```
INFO:__main__:Nueva consulta recibida: {'consulta': '...'}
INFO:__main__:Memoria creada para usuario: usuario1
INFO:__main__:Parametros extraidos por el agente: query='python' provincia='Madrid'
INFO:__main__:Resultados obtenidos: 5 ofertas encontradas
```

### Niveles de log

- `INFO`: Operaciones normales
- `WARNING`: Situaciones no críticas (provincia no reconocida)
- `ERROR`: Errores capturados con traceback completo

---

## Capacidades del Agente

El agente puede:

**Interpretar lenguaje natural**

- "Busco trabajo de Python en Madrid"
- "Desarrollador Java remoto"
- "Enfermero con experiencia en Valencia"

**Mantener contexto conversacional**

- Usuario: "Busco trabajos de Python"
- Usuario: "Ahora en Barcelona" → Recuerda Python

**Normalizar provincias**

- "barcelona" → ID `8`
- "MADRID" → ID `33`
- "sevilla" → ID `41`

**Detectar teletrabajo automáticamente**

- "remoto", "teletrabajo", "desde casa" → `teletrabajo: true`

**Generar resúmenes de conversación**

- Usa GPT-4o-mini para resumir historial largo

---

## Seguridad

### Buenas Prácticas Implementadas

- Variables de entorno para secretos
- `.gitignore` configurado para proteger `.env`
- Sin hardcodeo de credenciales
- Logging sin exponer datos sensibles

### Recomendaciones

- **Nunca** subas el archivo `.env` a repositorios públicos
- Revoca inmediatamente cualquier API key filtrada
- Usa entornos separados para desarrollo y producción
- Implementa rate limiting en producción

---

## Provincias Soportadas

El agente reconoce las **52 provincias españolas**:

<details>
<summary>Ver lista completa (click para expandir)</summary>

| Provincia      | ID  | Provincia   | ID  |
| -------------- | --- | ----------- | --- |
| A Coruña       | 15  | Álava       | 1   |
| Albacete       | 2   | Alicante    | 3   |
| Almería        | 4   | Asturias    | 33  |
| Ávila          | 5   | Badajoz     | 6   |
| Barcelona      | 8   | Burgos      | 9   |
| Cáceres        | 10  | Cádiz       | 11  |
| Cantabria      | 39  | Castellón   | 12  |
| Ceuta          | 51  | Ciudad Real | 13  |
| Córdoba        | 14  | Cuenca      | 16  |
| Girona         | 17  | Granada     | 18  |
| Guadalajara    | 19  | Gipuzkoa    | 20  |
| Huelva         | 21  | Huesca      | 22  |
| Islas Baleares | 7   | Jaén        | 23  |
| La Rioja       | 26  | Las Palmas  | 35  |
| León           | 24  | Lleida      | 25  |
| Lugo           | 27  | Madrid      | 28  |
| Málaga         | 29  | Melilla     | 52  |
| Murcia         | 30  | Navarra     | 31  |
| Ourense        | 32  | Palencia    | 34  |
| Pontevedra     | 36  | Salamanca   | 37  |
| Segovia        | 40  | Sevilla     | 41  |
| Soria          | 42  | Tarragona   | 43  |
| Tenerife       | 38  | Teruel      | 44  |
| Toledo         | 45  | Valencia    | 46  |
| Valladolid     | 47  | Bizkaia     | 48  |
| Zamora         | 49  | Zaragoza    | 50  |

</details>

---

## Licencia

Este proyecto está bajo la licencia MIT. Ver archivo [LICENSE](LICENSE) para más detalles.

---

## Soporte

Si encuentras algún problema o tienes sugerencias:

1. Revisa la sección [Resolución de Problemas](#resolución-de-problemas)
2. Consulta los logs de Flask para más detalles
3. Abre un Issue en GitHub

---

## Aprendizajes del Proyecto

Este proyecto demuestra:

- Integración de LLMs con aplicaciones web
- Implementación de memoria conversacional
- Structured output con Pydantic y LangChain
- Normalización de texto en español
- Diseño de APIs RESTful
- Manejo profesional de errores y logging
- Buenas prácticas de seguridad con variables de entorno

---

**Desarrollado usando Python, Flask y GPT-4o-mini**
