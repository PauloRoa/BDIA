# registro_rag.py
# Instrumentación del flujo RAG: mide el tiempo de cada etapa y los tokens reales de la generación, y guarda cada corrida como una línea JSON.

import json
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from cliente import PRECIO_ENTRADA, PRECIO_SALIDA
from consumir_gemini import MODELO
from indexar_corpus import (
    cargar_vectorstore,
    construir_embeddings,
)
from recuperacion import K_POR_DEFECTO, PROMPT_TEMPLATE, formatear_contexto

RUTA_REGISTROS = Path(__file__).resolve().parents[1] / "docs" / "registros_latencia_costo.jsonl"

# Preguntas del conjunto de evaluación de la recuperación, de distinto largo.
PREGUNTAS_DE_REGISTRO = [
    "¿Qué hace ON DELETE CASCADE en una clave foránea?",
    "¿Hay diferencia de rendimiento entre text y varchar(n)?",
    "¿Qué crea PostgreSQL automáticamente al definir una clave primaria?",
]


@contextmanager
def medir(tiempos, etapa):
    """Mide cuánto tarda el bloque with y lo guarda en tiempos[etapa], en segundos."""
    # perf_counter es un reloj monótono: los ajustes de hora del sistema no lo afectan.
    inicio = time.perf_counter()
    yield
    tiempos[etapa] = time.perf_counter() - inicio


def calcular_costo_tokens(tokens_entrada, tokens_salida):
    """Costo en dólares de una llamada, con los precios por token de cliente.py.
    Los tokens de salida ya incluyen los de razonamiento del modelo."""
    return round(tokens_entrada * PRECIO_ENTRADA + tokens_salida * PRECIO_SALIDA, 6)


def construir_modelo():
    """Modelo de generación, con la misma clave y modelo que el resto del proyecto."""
    return ChatGoogleGenerativeAI(
        model=MODELO,
        google_api_key=os.getenv("API_KEY"),
        temperature=0,
        timeout=60,
    )


def registrar_consulta(pregunta, embeddings, vectorstore, modelo, k=K_POR_DEFECTO):
    """Corre una consulta RAG real y devuelve el registro con el tiempo de cada
    etapa, los tokens reales de la respuesta y su costo."""
    # Se valida antes de gastar llamadas a la API.
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("La pregunta no puede estar vacía.")
    if k < 1:
        raise ValueError("k debe ser al menos 1.")
    tiempos = {}

    # El embedding se calcula aparte y la búsqueda recibe el vector ya listo:
    # así cada etapa se mide por separado y el embedding se calcula una sola vez.
    with medir(tiempos, "embed_query"):
        vector = embeddings.embed_query(pregunta)
    with medir(tiempos, "busqueda_vectorial"):
        chunks = vectorstore.similarity_search_by_vector(vector, k=k)

    # Un índice vacío o inexistente no genera un registro: sus tiempos y tokens no corresponderían a un flujo RAG real.
    if not chunks:
        raise ValueError("No se recuperó ningún chunk: ejecuta antes src/indexar_corpus.py.")

    contexto, _ = formatear_contexto(chunks)
    prompt = PROMPT_TEMPLATE.format(contexto=contexto, pregunta=pregunta)

    with medir(tiempos, "generacion"):
        respuesta = modelo.invoke(prompt)

    # usage_metadata trae los tokens reales de esta llamada; puede faltar.
    tokens = dict(respuesta.usage_metadata) if respuesta.usage_metadata else None
    costo_usd = None
    if tokens:
        costo_usd = calcular_costo_tokens(tokens["input_tokens"], tokens["output_tokens"])

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pregunta": pregunta,
        "k": k,
        "tiempos_ms": {etapa: round(seg * 1000, 2) for etapa, seg in tiempos.items()},
        "tiempo_total_ms": round(sum(tiempos.values()) * 1000, 2),
        "tokens": tokens,
        "costo_usd": costo_usd,
    }


def guardar_registro(registro, ruta=RUTA_REGISTROS):
    """Agrega el registro como una línea JSON al final del archivo."""
    with open(ruta, "a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    load_dotenv()
    try:
        k = int(sys.argv[1]) if len(sys.argv) > 1 else K_POR_DEFECTO
        embeddings = construir_embeddings()
        vectorstore = cargar_vectorstore(embeddings)
        modelo = construir_modelo()
        for pregunta in PREGUNTAS_DE_REGISTRO:
            registro = registrar_consulta(pregunta, embeddings, vectorstore, modelo, k)
            # Se guarda cada línea apenas se obtiene: una falla posterior no la pierde.
            guardar_registro(registro)
            print(json.dumps(registro, indent=2, ensure_ascii=False))
    except Exception as error:
        print("No se pudo registrar la consulta:", type(error).__name__)
        print("Detalle técnico:", error)
        raise SystemExit(1)
    print("Registros agregados a", RUTA_REGISTROS)