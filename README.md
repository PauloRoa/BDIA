# Proyecto BDIA

Repositorio del proyecto de la especialización en IA avanzada (Skillnest / Accenture). Contiene un cliente Python para la API de Google Gemini que arma las peticiones, clasifica los errores del proveedor, reintenta automáticamente los que son momentáneos con backoff exponencial y registra el costo de cada operación. Incluye además la comparación de modelos candidatos, el registro de la decisión de arquitectura sobre el modelo utilizado y un banco de prompts de sistema con salida JSON estructurada, validado por consistencia.

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

Con el entorno activo, desde la raíz del repositorio:

```
python src/cliente.py
```

Envía una pregunta fija al modelo a través de `consultar_modelo`, el punto de entrada del cliente, y muestra el costo de la operación y el texto generado. Si el proveedor falla de forma momentánea, el cliente reintenta automáticamente. La respuesta varía en cada ejecución, porque proviene de un modelo generativo. Para cambiar la pregunta, se edita la llamada final del archivo.

```
python src/consumir_gemini.py
```

Envía una pregunta fija al modelo `gemini-3.1-flash-lite` (constante `MODELO`) directamente, sin reintentos, y muestra el texto generado.

Scripts complementarios, que se ejecutan de la misma forma:

```
python src/contar_tokens.py
```

Envía una pregunta fija y muestra los tokens de entrada y de salida de la petición, junto con su costo en dólares, calculado con los precios de `gemini-3.1-flash-lite`.

```
python src/comparar_modelos.py
```

Compara dos modelos candidatos (`gemini-3.5-flash-lite` y `gemini-3.1-flash-lite`): repite cuatro veces una misma pregunta para medir latencia y costo, y envía una segunda pregunta para evaluar la calidad de la respuesta. Realiza 10 peticiones por ejecución. El análisis y la decisión se registran en `docs/decision-arquitectura.md`.

```
python prompts/test_consistencia.py
```

Ejecuta tres veces cada prompt del banco (`prompts/banco.py`), valida que la respuesta sea un JSON con las claves esperadas y guarda el resultado en `prompts/registro_resultados.json`. Realiza 9 peticiones por ejecución.

## Pruebas

Las pruebas unitarias del cliente están en `tests/test_cliente.py`. Simulan la API y las esperas con mocks, por lo que no consumen tokens ni requieren conexión. Con el entorno activo, desde la raíz del repositorio:

```
pytest tests/test_cliente.py -v
```

## Cliente `src/cliente.py`

Interfaz pública para consultar el modelo. Usa las funciones de `src/consumir_gemini.py` y agrega el reintento y el registro de costo, de modo que quien lo usa no necesita conocer el orden de las llamadas ni cómo se manejan los errores por dentro. El costo se calcula con los precios de `gemini-3.1-flash-lite` (constantes `PRECIO_ENTRADA` y `PRECIO_SALIDA`) y se acumula en `costo_total_sesion`, que vuelve a cero en cada ejecución.

| Función | Responsabilidad |
|---|---|
| `consultar_modelo(pregunta, system_instruction)` | Punto de entrada único: arma la petición, la envía con reintento, registra su costo y devuelve el texto generado. `system_instruction` es opcional. Si se agotan los reintentos, lanza `RuntimeError` con un mensaje para quien usa el cliente. |
| `con_reintento(funcion, intentos, espera_base, espera_maxima)` | Ejecuta una función sin argumentos y, si lanza `TimeoutError`, muestra el motivo, espera y la vuelve a intentar. La espera se duplica en cada intento a partir de `espera_base` (backoff exponencial), nunca supera `espera_maxima` y suma hasta un 10 % aleatorio (jitter). Por defecto: 3 intentos, base de 2 segundos y máximo de 30, es decir, esperas de 2 y 4 segundos. En el último intento deja pasar el error. Cualquier otra excepción se propaga sin reintentar. |
| `registrar_costo(respuesta)` | Calcula el costo de una operación exitosa con `calcular_costo`, lo suma a `costo_total_sesion`, muestra los tokens, el costo de la operación y el acumulado, y lo devuelve. Si la respuesta no trae el conteo de tokens, avisa y registra 0, sin impedir que se entregue la respuesta. |

Ejemplo de uso desde otro archivo de `src/`:

```python
from cliente import consultar_modelo

try:
    print(consultar_modelo("¿Cuál es la capital de Chile?"))
except ValueError as error:
    print(f"Error de configuración: {error}")
except RuntimeError as error:
    print(f"El servicio no respondió tras varios intentos: {error}")
```

## Módulo `src/consumir_gemini.py`

Cada función tiene una única responsabilidad:

| Función | Responsabilidad |
|---|---|
| `armar_peticion(prompt, modelo, system_instruction, response_schema)` | Valida la pregunta y arma la URL (según el modelo indicado, por defecto `MODELO`), los encabezados (la clave viaja en `x-goog-api-key`) y el cuerpo de la petición. Si se indica `system_instruction`, la agrega como `systemInstruction`, separada de la pregunta. Si se indica `response_schema`, agrega `generationConfig` para que la respuesta sea un JSON con esa estructura. Ambos parámetros son opcionales. |
| `enviar_peticion(url, headers, body)` | Envía la petición (con un tiempo de espera de 60 segundos), clasifica las fallas según si conviene reintentar y devuelve la respuesta convertida desde JSON. |
| `extraer_texto(respuesta_json)` | Navega la respuesta hasta el texto generado. |
| `parsear_respuesta_json(texto, claves_esperadas)` | Quita las marcas de markdown del texto, lo convierte desde JSON y comprueba que sea un objeto con las claves esperadas. |
| `calcular_costo(respuesta_json, precio_entrada, precio_salida)` | Calcula el costo en dólares de una petición a partir de `usageMetadata`: los tokens de entrada y de salida, multiplicados por su precio por token. |
| `generar_respuesta(prompt)` | Llama a `armar_peticion`, `enviar_peticion` y `extraer_texto` en orden, sin reintentos. |

## Manejo de errores

Cada falla se captura en la función a la que corresponde y se informa con un mensaje que indica qué ocurrió. El tipo de excepción indica qué hacer con ella:

- `ValueError`: problema de entrada o de configuración. Reintentar no lo soluciona; hay que corregirlo.
- `TimeoutError`: falla momentánea del proveedor o de la red. Reintentar después de esperar suele resolverla.
- `RuntimeError`: respuesta inesperada del servicio o reintentos agotados.

| Falla | Dónde se maneja | Excepción | Mensaje |
|---|---|---|---|
| Pregunta vacía | `armar_peticion` | `ValueError` | `La pregunta no puede estar vacía.` |
| Servicio sin conexión o tiempo de espera agotado | `enviar_peticion` | `TimeoutError` | `No se pudo contactar al proveedor. Puede ser momentáneo: …` |
| Credencial inválida o sin permiso (HTTP 401 o 403, o HTTP 400 con motivo `API_KEY_INVALID`, que es lo que informa Gemini) | `enviar_peticion` | `ValueError` | `Credencial inválida o sin permiso. Revisa tu API_KEY.` |
| Límite de uso excedido (HTTP 429) o falla del proveedor (HTTP 500 o superior) | `enviar_peticion` | `TimeoutError` | `El proveedor no pudo procesar la petición (HTTP …). Hay que esperar y reintentar.` |
| Respuesta del servicio que no es JSON válido | `enviar_peticion` | `RuntimeError` | `La respuesta del servicio no llegó en el formato esperado: …` |
| Otro error informado por el servicio | `enviar_peticion` | `RuntimeError` | `El servicio rechazó la petición (HTTP …): …` (con el mensaje del servicio) |
| Texto ausente en la respuesta | `extraer_texto` | `RuntimeError` | `La respuesta no trae el texto generado en el lugar esperado: …` |
| Texto del modelo que no es JSON válido | `parsear_respuesta_json` | `ValueError` | `La respuesta del modelo no es JSON válido.` |
| JSON sin la estructura esperada | `parsear_respuesta_json` | `ValueError` | `La respuesta no tiene la estructura esperada.` |
| Conteo de tokens ausente en la respuesta | `calcular_costo` | `RuntimeError` | `La respuesta no trae el conteo de tokens en el lugar esperado: …` |
| Reintentos agotados | `consultar_modelo` | `RuntimeError` | `El servicio no respondió tras varios intentos. Intenta más tarde.` |

La llamada final de `consumir_gemini.py` captura los tres tipos de excepción y muestra `No se pudo generar la respuesta: <mensaje>`. La de `cliente.py` captura `ValueError` y `RuntimeError`, porque `consultar_modelo` ya convierte el `TimeoutError` final en `RuntimeError`.

## Estructura del repositorio

- `src/`: código fuente.
- `prompts/`: banco de prompts (`banco.py`), script de prueba de consistencia (`test_consistencia.py`) y su registro de resultados (`registro_resultados.json`).
- `docs/`: documentación y evidencias. Incluye la evidencia de la primera petición autenticada (`evidencia_peticion_autenticada.txt` y `.png`), el diagrama de arquitectura (`diagrama_arquitectura.png`), el registro de la decisión de arquitectura (`decision-arquitectura.md`), los datos de la comparación de modelos (`resultados_comparacion.json`) y el registro de los ensayos de instalación limpia y de rate limit (`registro_ensayos.md`).
- `tests/`: pruebas unitarias del cliente (`test_cliente.py`).
- `pytest.ini`: configuración de pytest; agrega `src/` a la ruta de importación para que las pruebas encuentren los módulos.
- `requirements.txt`: dependencias de Python.
- `.env.example`: plantilla de variables de entorno, sin valores reales.

## Reglas de seguridad

- Ningún secreto (clave de API, token) se escribe en el código ni en archivos versionados.
- Las claves viven solo en `.env`.