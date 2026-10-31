import os
import re

from cliente import consultar_modelo

RUTA_REGISTRO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "registro_pipeline_texto.md"))

SYSTEM_INSTRUCTION = "Responde en una sola oración, sin formato markdown."

CASOS = [
    {
        "pregunta": "¿Qué es una clave primaria en una base de datos relacional?",
        "referencia": "Una clave primaria es una columna o conjunto de columnas que identifica de forma única cada fila de una tabla.",
    },
    {
        "pregunta": "¿Qué es una clave foránea en una base de datos relacional?",
        "referencia": "Una clave foránea es una columna que referencia la clave primaria de otra tabla para relacionar ambas tablas.",
    },
    {
        "pregunta": "¿Qué es la normalización de una base de datos relacional?",
        "referencia": "La normalización es el proceso de organizar las tablas de una base de datos para reducir la redundancia y evitar anomalías al modificar los datos.",
    },
]


def limpiar_texto(texto: str) -> str:
    """Normaliza el texto: minúsculas, sin puntuación y sin espacios repetidos."""
    if not isinstance(texto, str):
        tipo = type(texto).__name__
        raise TypeError(f"limpiar_texto espera str, no {tipo}")
    texto = texto.lower()
    texto = re.sub(r"[^\w\s]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def tokenizar(texto_limpio: str) -> list[str]:
    """Convierte texto limpio en una lista de tokens."""
    return texto_limpio.split()


def procesar_texto(texto: str) -> list[str]:
    """Limpia y tokeniza el texto en un solo paso."""
    return tokenizar(limpiar_texto(texto))


def calcular_coincidencia(tokens_referencia: list[str], tokens_respuesta: list[str]) -> float:
    """Proporción de palabras distintas de la referencia que también aparecen en la respuesta."""
    if not tokens_referencia:
        return 0.0
    comunes = set(tokens_referencia) & set(tokens_respuesta)
    return len(comunes) / len(set(tokens_referencia))


if __name__ == "__main__":
    lineas = [
        "# Registro del pipeline de texto",
        "",
        "Coincidencia por palabras entre una referencia propia y la respuesta del modelo, calculada sobre texto crudo y sobre texto procesado con `procesar_texto`.",
        "",
    ]
    for numero, caso in enumerate(CASOS, start=1):
        try:
            respuesta = consultar_modelo(caso["pregunta"], system_instruction=SYSTEM_INSTRUCTION)
        except (ValueError, RuntimeError) as error:
            print(f"[Caso {numero}] No se pudo obtener la respuesta: {error}")
            continue
        pct_crudo = calcular_coincidencia(caso["referencia"].split(), respuesta.split())
        pct_procesado = calcular_coincidencia(procesar_texto(caso["referencia"]), procesar_texto(respuesta))
        print(f"[Caso {numero}] Coincidencia texto crudo: {pct_crudo:.1%}")
        print(f"[Caso {numero}] Coincidencia texto procesado: {pct_procesado:.1%}")
        lineas += [
            f"## Caso {numero}",
            "",
            f"- Pregunta: {caso['pregunta']}",
            f"- Referencia: {caso['referencia']}",
            f"- Respuesta: {' '.join(respuesta.split())}",
            f"- Coincidencia texto crudo: {pct_crudo:.1%}",
            f"- Coincidencia texto procesado: {pct_procesado:.1%}",
            "",
        ]
    with open(RUTA_REGISTRO, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas))
    print(f"Registro guardado en {RUTA_REGISTRO}")