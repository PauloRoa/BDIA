# Proyecto BDIA

Repositorio del proyecto de la especialización en IA avanzada (Skillnest / Accenture). Contiene la habilitación técnica del Módulo 1: repositorio, entorno reproducible y un módulo Python que consume la API de Google Gemini, procesa la respuesta JSON, gestiona los errores previsibles y calcula el costo de cada petición. Incluye además la comparación de modelos candidatos, el registro de la decisión de arquitectura sobre el modelo utilizado y un banco de prompts de sistema con salida JSON estructurada, validado por consistencia.

**Estado actual:** Módulo 1 (Gate 1) completado.

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
python src/consumir_gemini.py
```

El módulo envía una pregunta fija al modelo `gemini-3.1-flash-lite` (constante `MODELO`) y muestra por pantalla el texto generado. La respuesta varía en cada ejecución, porque proviene de un modelo generativo. Para cambiar la pregunta, se edita la llamada final del archivo.

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

## Módulo `src/consumir_gemini.py`

Cada función tiene una única responsabilidad:

| Función | Responsabilidad |
|---|---|
| `armar_peticion(prompt, modelo, system_instruction, response_schema)` | Valida la pregunta y arma la URL (según el modelo indicado, por defecto `MODELO`), los encabezados (la clave viaja en `x-goog-api-key`) y el cuerpo de la petición. Si se indica `system_instruction`, la agrega como `systemInstruction`, separada de la pregunta. Si se indica `response_schema`, agrega `generationConfig` para que la respuesta sea un JSON con esa estructura. Ambos parámetros son opcionales. |
| `enviar_peticion(url, headers, body)` | Envía la petición (con un tiempo de espera de 60 segundos) y devuelve la respuesta convertida desde JSON. |
| `extraer_texto(respuesta_json)` | Navega la respuesta hasta el texto generado. |
| `parsear_respuesta_json(texto, claves_esperadas)` | Quita las marcas de markdown del texto, lo convierte desde JSON y comprueba que sea un objeto con las claves esperadas. |
| `calcular_costo(respuesta_json, precio_entrada, precio_salida)` | Calcula el costo en dólares de una petición a partir de `usageMetadata`: los tokens de entrada y de salida, multiplicados por su precio por token. |
| `generar_respuesta(prompt)` | Función principal: llama a `armar_peticion`, `enviar_peticion` y `extraer_texto` en orden. |

## Manejo de errores

Cada falla se captura en la función a la que corresponde y se informa con un mensaje que indica qué ocurrió. Quien llama a `generar_respuesta` recibe `ValueError` o `RuntimeError`, y el programa no se detiene sin control.

| Falla | Dónde se maneja | Mensaje |
|---|---|---|
| Pregunta vacía | `armar_peticion` | `La pregunta no puede estar vacía.` |
| Servicio sin conexión o tiempo de espera agotado | `enviar_peticion` | `No se pudo conectar con el servicio o se agotó el tiempo de espera: …` |
| Respuesta del servicio que no es JSON válido | `enviar_peticion` | `La respuesta del servicio no llegó en el formato esperado: …` |
| Error informado por el servicio (clave inválida, alta demanda, cuota excedida) | `enviar_peticion` | `El servicio rechazó la petición: …` (con el mensaje del servicio) |
| Texto ausente en la respuesta | `extraer_texto` | `La respuesta no trae el texto generado en el lugar esperado: …` |
| Texto del modelo que no es JSON válido | `parsear_respuesta_json` | `La respuesta del modelo no es JSON válido.` |
| JSON sin la estructura esperada | `parsear_respuesta_json` | `La respuesta no tiene la estructura esperada.` |
| Conteo de tokens ausente en la respuesta | `calcular_costo` | `La respuesta no trae el conteo de tokens en el lugar esperado: …` |

La llamada final del módulo captura ambos tipos de excepción y muestra `No se pudo generar la respuesta: <mensaje>`.

## Estructura del repositorio

- `src/`: código fuente.
- `prompts/`: banco de prompts (`banco.py`), script de prueba de consistencia (`test_consistencia.py`) y su registro de resultados (`registro_resultados.json`).
- `docs/`: documentación y evidencias. Incluye la evidencia de la primera petición autenticada (`evidencia_peticion_autenticada.txt` y `.png`), el diagrama de arquitectura (`diagrama_arquitectura.png`), el registro de la decisión de arquitectura (`decision-arquitectura.md`) y los datos de la comparación de modelos (`resultados_comparacion.json`).
- `tests/`: reservada para pruebas automatizadas (aún sin contenido).
- `requirements.txt`: dependencias de Python.
- `.env.example`: plantilla de variables de entorno, sin valores reales.

## Reglas de seguridad

- Ningún secreto (clave de API, token) se escribe en el código ni en archivos versionados.
- Las claves viven solo en `.env`.

## Registro del ensayo de instalación limpia

- Fecha: 2026-10-24
- Alcance: clon desde GitHub en una carpeta nueva, con entorno virtual nuevo, en el mismo equipo de desarrollo.
- Encontrado: el README no incluía el paso de clonado del repositorio.
- Corregido: se agregó el paso de clonado al README y se confirmó que el resto de los pasos funciona siguiendo solo sus instrucciones.
- Resultado tras la corrección: instalación y ejecución de `python src/consumir_gemini.py` sin intervención manual, con respuesta real del modelo y sin errores. `git status` quedó limpio, `.env` no está versionado y no aparece en el historial.