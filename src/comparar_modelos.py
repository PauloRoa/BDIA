import time

from consumir_gemini import armar_peticion, enviar_peticion, extraer_texto, calcular_costo

# Precios del nivel pagado, en USD por 1 millón de tokens
MODELOS = {
    "gemini-3.5-flash-lite": {"entrada": 0.30, "salida": 2.50},
    "gemini-3.1-flash-lite": {"entrada": 0.25, "salida": 1.50},
}

REPETICIONES = 4

PREGUNTA_LATENCIA = (
    "Una pyme que vende ropa por internet necesita una base de datos relacional nueva. "
    "Sin crear el esquema, indica en máximo 5 líneas qué tablas principales propondrías "
    "y cómo se relacionan entre sí."
)
PREGUNTA_CALIDAD = (
    "Un almacén de barrio necesita unir sus ventas y su inventario en una sola base de datos "
    "relacional. Sin crear el esquema, explica en máximo 6 líneas qué tablas propondrías, "
    "cómo manejarías los precios y cómo registrarías las entradas y salidas de mercadería."
)


def medir_modelo(modelo, precios):
    precio_entrada = precios["entrada"] / 1_000_000
    precio_salida = precios["salida"] / 1_000_000
    latencias = []
    costos = []
    for _ in range(REPETICIONES):
        url, headers, body = armar_peticion(PREGUNTA_LATENCIA, modelo)
        inicio = time.perf_counter()
        respuesta_json = enviar_peticion(url, headers, body)
        latencias.append(time.perf_counter() - inicio)
        costos.append(calcular_costo(respuesta_json, precio_entrada, precio_salida))
    respuesta_1 = extraer_texto(respuesta_json)
    uso = respuesta_json["usageMetadata"]

    url, headers, body = armar_peticion(PREGUNTA_CALIDAD, modelo)
    respuesta_2 = extraer_texto(enviar_peticion(url, headers, body))

    return {
        "latencias": latencias,
        "latencia_promedio": sum(latencias) / len(latencias),
        "costo_promedio": sum(costos) / len(costos),
        "uso": uso,
        "respuesta_1": respuesta_1,
        "respuesta_2": respuesta_2,
    }


def mostrar_resultado(modelo, resultado):
    print(f"\n=== {modelo} ===")
    for numero, latencia in enumerate(resultado["latencias"], start=1):
        print(f"Intento {numero}: {latencia:.2f} segundos")
    print(f"Latencia promedio: {resultado['latencia_promedio']:.2f} segundos")
    print(f"Costo promedio por petición: US$ {resultado['costo_promedio']:.8f}")
    print(f"Uso de tokens (última petición): {resultado['uso']}")
    print(f"\nRespuesta pregunta 1:\n{resultado['respuesta_1']}")
    print(f"\nRespuesta pregunta 2:\n{resultado['respuesta_2']}")


if __name__ == "__main__":
    for modelo, precios in MODELOS.items():
        try:
            resultado = medir_modelo(modelo, precios)
        except (ValueError, RuntimeError) as error:
            print(f"No se pudo medir {modelo}: {error}")
            continue
        mostrar_resultado(modelo, resultado)