# Proyecto BDIA

Repositorio del proyecto de la especialización en IA avanzada (Skillnest / Accenture). Contiene la habilitación técnica del Módulo 1: repositorio, entorno reproducible y un módulo Python que consume la API de Google Gemini, procesa la respuesta JSON y gestiona los errores previsibles.

**Estado actual:** Unidad U1.3 (Python aplicado para integración con IA) completada.

## Requisitos

- Python 3.13 (probado con 3.13.0)
- Git
- Una API key de Google Gemini, creada en Google AI Studio

## Puesta en marcha

1. Crear el entorno virtual:

```
python -m venv .venv
```

2. Activarlo (cada terminal necesita su propia activación):

Git Bash:

```
source .venv/Scripts/activate
```

PowerShell:

```
.\.venv\Scripts\Activate.ps1
```

3. Instalar las dependencias:

```
pip install -r requirements.txt
```

4. Crear el archivo de variables de entorno a partir de la plantilla:

```
cp .env.example .env
```

5. Abrir `.env` y reemplazar el marcador por tu clave real en la variable `API_KEY`. El archivo `.env` está excluido en `.gitignore` y nunca se sube al repositorio.

## Uso

Con el entorno activo, desde la raíz del repositorio:

```
python src/consumir_gemini.py
```

El módulo envía una pregunta fija al modelo `gemini-flash-latest` y muestra por pantalla el texto generado. La respuesta varía en cada ejecución, porque proviene de un modelo generativo. Para cambiar la pregunta, se edita la llamada final del archivo.

Al ejecutarse, el módulo realiza esa consulta de inmediato; todavía no está preparado para importarse sin que se envíe una petición.

## Módulo `src/consumir_gemini.py`

Cada función tiene una única responsabilidad:

| Función | Responsabilidad |
|---|---|
| `armar_peticion(prompt)` | Valida la pregunta y arma la URL, los encabezados (la clave viaja en `x-goog-api-key`) y el cuerpo de la petición. |
| `enviar_peticion(url, headers, body)` | Envía la petición (con un tiempo de espera de 60 segundos) y devuelve la respuesta convertida desde JSON. |
| `extraer_texto(respuesta_json)` | Navega la respuesta hasta el texto generado. |
| `generar_respuesta(prompt)` | Función principal: llama a las tres anteriores en orden. |

## Manejo de errores

Cada falla se captura en la función a la que corresponde y se informa con un mensaje que indica qué ocurrió. Quien llama a `generar_respuesta` recibe `ValueError` o `RuntimeError`, y el programa no se detiene sin control.

| Falla | Dónde se maneja | Mensaje |
|---|---|---|
| Pregunta vacía | `armar_peticion` | `La pregunta no puede estar vacía.` |
| Servicio sin conexión o tiempo de espera agotado | `enviar_peticion` | `No se pudo conectar con el servicio o se agotó el tiempo de espera: …` |
| Respuesta que no es JSON válido | `enviar_peticion` | `La respuesta del servicio no llegó en el formato esperado: …` |
| Error informado por el servicio (clave inválida, alta demanda, cuota excedida) | `enviar_peticion` | `El servicio rechazó la petición: …` (con el mensaje del servicio) |
| Texto ausente en la respuesta | `extraer_texto` | `La respuesta no trae el texto generado en el lugar esperado: …` |

La llamada final del módulo captura ambos tipos de excepción y muestra `No se pudo generar la respuesta: <mensaje>`.

## Estructura del repositorio

- `src/`: código fuente.
- `docs/`: documentación y evidencias. Incluye la evidencia de la primera petición autenticada (`evidencia_peticion_autenticada.txt` y `.png`).
- `tests/`: pruebas.
- `requirements.txt`: dependencias de Python.
- `.env.example`: plantilla de variables de entorno, sin valores reales.

## Reglas de seguridad

- Ningún secreto (clave de API, token) se escribe en el código ni en archivos versionados.
- Las claves viven solo en `.env`.