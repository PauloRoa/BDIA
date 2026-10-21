from consumir_gemini import armar_peticion, enviar_peticion, extraer_texto, calcular_costo

# Precios del nivel pagado de Gemini 3.8 Flash, en USD por token
# (0,75 y 3,75 por 1 millón de tokens, vigentes hasta el 31-12-2026)
PRECIO_ENTRADA = 0.75 / 1_000_000
PRECIO_SALIDA = 3.75 / 1_000_000

PROMPT = "Explica en dos frases qué es un token en un modelo de lenguaje."

try:
    url, headers, body = armar_peticion(PROMPT)
    respuesta_json = enviar_peticion(url, headers, body)
    texto = extraer_texto(respuesta_json)
    costo_entrada = calcular_costo(respuesta_json, PRECIO_ENTRADA, 0)
    costo_salida = calcular_costo(respuesta_json, 0, PRECIO_SALIDA)
    uso = respuesta_json["usageMetadata"]
except (ValueError, RuntimeError) as error:
    print(f"No se pudo calcular el uso de tokens: {error}")
else:
    print(f"Respuesta: {texto}")
    print(f"Tokens de entrada: {uso['promptTokenCount']} -> US$ {costo_entrada:.8f}")
    print(f"Tokens de salida: {uso['candidatesTokenCount']} -> US$ {costo_salida:.8f}")
    print(f"Total de tokens: {uso['totalTokenCount']} -> US$ {costo_entrada + costo_salida:.8f}")
    print("Costo estimado con precios de pago de Gemini 3.8 Flash; el nivel gratuito no tiene costo.")