import json
import os
import sys
import time

RUTA_PROMPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RUTA_PROMPTS, "..", "src"))

from banco import BANCO_DE_PROMPTS
from consumir_gemini import armar_peticion, enviar_peticion, extraer_texto, parsear_respuesta_json

INTENTOS = 3
PAUSA_ENTRE_LLAMADAS = 1
ARCHIVO_REGISTRO = os.path.join(RUTA_PROMPTS, "registro_resultados.json")

registro = {}

for prompt in BANCO_DE_PROMPTS:
    exitos = 0
    for intento in range(INTENTOS):
        try:
            url, headers, body = armar_peticion(
                prompt["ejemplo_usuario"],
                system_instruction=prompt["system_instruction"],
                response_schema=prompt.get("response_schema"),
            )
            respuesta = enviar_peticion(url, headers, body)
            texto = extraer_texto(respuesta)
            parsear_respuesta_json(texto, prompt["claves_esperadas"])
            exitos += 1
        except (ValueError, RuntimeError) as error:
            print(f"  intento {intento + 1} falló: {error}")
        time.sleep(PAUSA_ENTRE_LLAMADAS)
    print(f"{prompt['nombre']}: {exitos}/{INTENTOS} respuestas válidas")
    registro[prompt["nombre"]] = {"exitos": exitos, "intentos": INTENTOS}

with open(ARCHIVO_REGISTRO, "w", encoding="utf-8") as archivo:
    json.dump(registro, archivo, indent=2, ensure_ascii=False)