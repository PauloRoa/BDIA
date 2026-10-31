import random
import time
from typing import Any, Callable

from consumir_gemini import armar_peticion, calcular_costo, enviar_peticion, extraer_texto

# Precios del nivel pagado de gemini-3.1-flash-lite, en USD por token
# (0,25 y 1,50 por 1 millón de tokens)
PRECIO_ENTRADA = 0.25 / 1_000_000
PRECIO_SALIDA = 1.50 / 1_000_000

costo_total_sesion = 0.0


def con_reintento(
    funcion: Callable[[], Any],
    intentos: int = 3,
    espera_base: float = 2,
    espera_maxima: float = 30,
) -> Any:
    for intento in range(1, intentos + 1):
        try:
            return funcion()
        except TimeoutError as error:
            if intento == intentos:
                raise
            espera = min(espera_base * (2 ** (intento - 1)), espera_maxima)
            espera_con_jitter = espera + random.uniform(0, espera * 0.1)
            print(f"Intento {intento} de {intentos} falló ({error}). Reintentando en {espera_con_jitter:.1f}s...")
            time.sleep(espera_con_jitter)


def registrar_costo(respuesta: dict) -> float:
    global costo_total_sesion
    try:
        costo_estimado = calcular_costo(respuesta, PRECIO_ENTRADA, PRECIO_SALIDA)
    except RuntimeError as error:
        print(f"No se pudo registrar el costo de la operación: {error}")
        return 0.0
    costo_total_sesion += costo_estimado
    total_tokens = respuesta["usageMetadata"].get("totalTokenCount", 0)
    print(f"Operación: {total_tokens} tokens, costo estimado: ${costo_estimado:.6f} (acumulado: ${costo_total_sesion:.6f})")
    return costo_estimado


def consultar_modelo(
    pregunta: str,
    system_instruction: str | None = None,
) -> str:
    url, headers, body = armar_peticion(pregunta, system_instruction=system_instruction)
    try:
        respuesta = con_reintento(lambda: enviar_peticion(url, headers, body))
    except TimeoutError:
        raise RuntimeError("El servicio no respondió tras varios intentos. Intenta más tarde.")
    registrar_costo(respuesta)
    return extraer_texto(respuesta)


if __name__ == "__main__":
    try:
        respuesta = consultar_modelo("¿Cuál es la capital de Chile?")
        print(respuesta)
    except ValueError as error:
        print(f"Error de configuración: {error}")
    except RuntimeError as error:
        print(f"El servicio no respondió tras varios intentos: {error}")