# Proyecto BDIA

Repositorio del proyecto de la especialización en IA avanzada (Skillnest / Accenture). A partir de la descripción de un negocio, genera el borrador del script de creación de una base de datos PostgreSQL nueva. Reúne un cliente para la API de Google Gemini con reintentos y registro de costo, un flujo orquestado con LangChain, un agente con herramientas, memoria y aprobación humana, y un flujo RAG con índice vectorial, recuperación con citas, evaluación y registro de latencia y costo. Incluye además el pipeline de texto con sus métricas, la comparación de modelos y el banco de prompts.

El detalle técnico de cada módulo está en [docs/referencia_tecnica.md](docs/referencia_tecnica.md).

## Requisitos

- Python 3.13 (probado con 3.13.0)
- Git
- Una API key de Google Gemini, creada en Google AI Studio

## Puesta en marcha

1. Clonar el repositorio y entrar a la carpeta:

```
git clone https://github.com/PauloRoa/BDIA.git
cd BDIA
```

2. Crear el entorno virtual:

```
python -m venv .venv
```

3. Activarlo (cada terminal necesita su propia activación):

Git Bash:

```
source .venv/Scripts/activate
```

PowerShell:

```
.\.venv\Scripts\Activate.ps1
```

4. Instalar las dependencias:

```
pip install -r requirements.txt
```

5. Crear el archivo de variables de entorno a partir de la plantilla:

```
cp .env.example .env
```

6. Abrir `.env` y reemplazar el marcador por tu clave real en la variable `API_KEY`. El archivo `.env` está excluido en `.gitignore` y nunca se sube al repositorio.

## Uso

Con el entorno activo, desde la raíz del repositorio, cada comando se ejecuta como `python <ruta>`:

| Comando | Qué hace | Consumo de la API |
|---|---|---|
| `python src/cliente.py` | Consulta fija al modelo, con reintentos y registro de costo | 1 petición, más los reintentos |
| `python src/consumir_gemini.py` | Consulta fija al modelo, sin reintentos | 1 petición |
| `python src/enrutamiento.py` | Clasifica 3 solicitudes de ejemplo y las dirige a su ruta: genera el script, rechaza la solicitud o pide una descripción del negocio | 8 peticiones |
| `python src/cadena_tres_pasos.py` | Genera el script de creación de la base de ejemplo, sin clasificación previa | 3 peticiones |
| `python src/agente_con_herramientas.py` | Agente con herramientas: 3 consultas de verificación | Varía según las decisiones del agente |
| `python src/agente_con_memoria.py` | Agente con memoria en una sesión; pide aprobación por consola (`s` aprueba) para guardar borradores y agrega trazas a `docs/trazas_agente.jsonl` | Varía según las decisiones del agente |
| `python src/indexar_corpus.py` | Indexa los documentos de `corpus/` en `vectorstore/` (14 chunks de 7 documentos) | Un embedding por chunk |
| `python src/recuperacion.py` | Responde 3 preguntas de ejemplo con los chunks recuperados y sus citas | 3 embeddings y 3 peticiones |
| `python src/evaluacion_recuperacion.py` | Mide la precisión y el recall de la recuperación con 11 preguntas etiquetadas y guarda el registro en `docs/` | 11 embeddings, sin generación |
| `python src/registro_rag.py` | Mide la latencia de cada etapa del flujo RAG y los tokens y el costo reales con 3 preguntas; agrega 3 líneas a `docs/registros_latencia_costo.jsonl` | 3 embeddings y 3 peticiones de generación |
| `python src/evaluar_salidas.py` | Calcula precisión, cobertura y F1 de 20 respuestas frente a una referencia propia y guarda `docs/resultados_metricas.json` | 20 peticiones |
| `python src/revision_manual.py` | Guarda la revisión manual de una muestra en `docs/revision_manual.json` | Ninguna |
| `python src/pipeline_texto.py` | Compara 3 respuestas con su referencia, sobre texto crudo y procesado, y guarda `docs/registro_pipeline_texto.md` | 3 peticiones |
| `python src/contar_tokens.py` | Muestra los tokens y el costo en dólares de una petición | 1 petición |
| `python src/comparar_modelos.py` | Compara dos modelos candidatos en latencia, costo y calidad | 10 peticiones |
| `python prompts/test_consistencia.py` | Ejecuta tres veces cada prompt del banco y valida su respuesta JSON | 9 peticiones |

- `recuperacion.py`, `evaluacion_recuperacion.py` y `registro_rag.py` requieren haber ejecutado antes `python src/indexar_corpus.py`.
- `evaluacion_recuperacion.py` y `registro_rag.py` aceptan la cantidad de chunks k como argumento (por defecto 3), por ejemplo `python src/registro_rag.py 6`.
- Los scripts con consumo de la API gastan tokens y varían entre ejecuciones, porque el modelo es generativo.
- `agente_con_memoria.py` modifica `docs/trazas_agente.jsonl`, que está versionado como evidencia. Para conservar la original: `git restore docs/trazas_agente.jsonl`.

La ejecución de cada script, sus salidas y sus fallas están en la [referencia técnica](docs/referencia_tecnica.md).

## Pruebas

Las pruebas unitarias están en `tests/`. Ninguna consume tokens ni requiere conexión: la API, el índice y las esperas se simulan. Con el entorno activo, desde la raíz del repositorio:

```
pytest tests/ -v
```

`pytest.ini` limita la búsqueda de pruebas a `tests/`, por lo que `prompts/test_consistencia.py`, que hace peticiones reales, no se ejecuta con `pytest`. La lista de pruebas por archivo está en la [referencia técnica](docs/referencia_tecnica.md#pruebas).

## Estructura del repositorio

- `src/`: código fuente.
- `corpus/`: documentos de buenas prácticas de modelado en PostgreSQL que se indexan.
- `prompts/`: banco de prompts (`banco.py`), script de prueba de consistencia (`test_consistencia.py`) y su registro de resultados (`registro_resultados.json`).
- `docs/`: documentación técnica (`referencia_tecnica.md`), evidencias y registros de las ejecuciones. El detalle de su contenido está en la referencia técnica. La carpeta `docs/borradores/`, donde el agente guarda los borradores aprobados, no se versiona.
- `tests/`: pruebas unitarias (`test_*.py`).
- `pytest.ini`: configuración de pytest; agrega `src/` a la ruta de importación para que las pruebas encuentren los módulos y limita la búsqueda de pruebas a `tests/`.
- `requirements.txt`: dependencias de Python.
- `.env.example`: plantilla de variables de entorno, sin valores reales.

La carpeta `vectorstore/`, que genera `src/indexar_corpus.py`, no se versiona.

## Reglas de seguridad

- Ningún secreto (clave de API, token) se escribe en el código ni en archivos versionados.
- Las claves viven solo en `.env`.
- Las acciones de riesgo alto del agente requieren aprobación humana explícita y, sin respuesta a tiempo, se rechazan.