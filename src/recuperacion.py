# recuperacion.py
# Recuperación semántica y prompt dinámico con fuente citada.
# Flujo: pregunta -> recuperar los k chunks más parecidos del índice guardado
# -> armar un contexto numerado -> armar un prompt que obliga a citar [N]
# -> enviarlo al modelo -> traducir cada [N] de la respuesta a su archivo.

import re

from dotenv import load_dotenv

from cliente import consultar_modelo
from indexar_corpus import (
    CARPETA_VECTORSTORE,
    cargar_vectorstore,
    construir_embeddings,
)

# Cantidad de chunks que se recuperan por pregunta. Más no siempre es mejor:
# chunks poco relevantes diluyen la atención del modelo.
K_POR_DEFECTO = 3

# Valor que se muestra cuando el modelo cita un número que no existe en el contexto.
FUENTE_INVALIDA = "cita inválida: el número no está en el contexto"

# Plantilla del prompt. Contiene tres instrucciones: usar SOLO el contexto,
# citar con [N] y admitir cuando el contexto no alcanza.
# La barra invertida al final de la línea une la oración siguiente en un solo
# renglón del prompt; no debe haber nada después de ella.
PROMPT_TEMPLATE = """Responde la pregunta usando SOLO el contexto de abajo. Cita la \
fuente de cada afirmación con su número entre corchetes, como [1]. Si el contexto no \
alcanza para responder, dilo explícitamente en vez de inventar.

Contexto:
{contexto}

Pregunta: {pregunta}

Respuesta:"""

# Preguntas del main: dos que el corpus responde y una de PostgreSQL que NO
# está en el corpus, para comprobar que el modelo admite que no tiene información.
PREGUNTAS_DE_PRUEBA = [
    "¿Para qué sirve una clave foránea?",
    "¿Cuándo conviene crear un índice?",
    "¿Cómo se configura la replicación en PostgreSQL?",
]


def formatear_contexto(chunks_recuperados):
    """Arma el contexto numerado para el prompt y un mapa número -> fuente
    para reconstruir la cita después."""
    lineas = []
    citas = {}
    # La numeración empieza en 1 porque es la que lee una persona: [1], [2]...
    for i, doc in enumerate(chunks_recuperados, start=1):
        # Si el chunk no se indexó con la clave "fuente", se usa "desconocida"
        # en vez de fallar. El error queda visible en las citas.
        fuente = doc.metadata.get("fuente", "desconocida")
        lineas.append(f"[{i}] {doc.page_content}")
        citas[i] = fuente
    # Una línea en blanco entre chunks para que el modelo los vea como bloques distintos.
    contexto = "\n\n".join(lineas)
    # El texto va al prompt; el diccionario se queda en el programa.
    return contexto, citas


def construir_prompt(pregunta, persist_directory=CARPETA_VECTORSTORE, k=K_POR_DEFECTO):
    """Recupera los k chunks más relevantes del índice guardado y arma el
    prompt con contexto numerado. Devuelve (prompt, citas)."""
    # Se valida antes de gastar una llamada a la API de embeddings.
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("La pregunta no puede estar vacía.")
    # Solo se reconecta al índice ya guardado: no se llama a from_documents,
    # que recalcularía los embeddings de todo el corpus en cada pregunta.
    vectorstore = cargar_vectorstore(construir_embeddings(), persist_directory)
    # as_retriever envuelve la búsqueda por similitud con la interfaz .invoke().
    # Aquí se calcula el embedding de la pregunta (consume tokens) y se buscan
    # los k vectores más cercanos.
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    chunks_recuperados = retriever.invoke(pregunta)
    contexto, citas = formatear_contexto(chunks_recuperados)
    # La pregunta se inserta sin modificarla.
    prompt = PROMPT_TEMPLATE.format(contexto=contexto, pregunta=pregunta)
    return prompt, citas


def resolver_citas(respuesta, citas):
    """Devuelve {número: fuente} para cada cita [N] de la respuesta. Un número
    que no está en el contexto se marca como inválido en vez de fallar."""
    # re.findall extrae todos los números entre corchetes; el set elimina
    # repetidos y sorted los deja en orden.
    numeros = sorted({int(numero) for numero in re.findall(r"\[(\d+)\]", respuesta)})
    # citas.get evita un KeyError si el modelo inventa un número como [99].
    return {numero: citas.get(numero, FUENTE_INVALIDA) for numero in numeros}


if __name__ == "__main__":
    load_dotenv()
    for pregunta in PREGUNTAS_DE_PRUEBA:
        print("=" * 60)
        print("Pregunta:", pregunta)
        try:
            prompt, citas = construir_prompt(pregunta)
            # El prompt completo se envía como la pregunta del cliente, que
            # ya trae reintentos y registro de costo.
            respuesta = consultar_modelo(prompt)
        except Exception as error:
            # Cualquier falla (clave, cuota, red) se informa sin traceback largo.
            print("No se pudo procesar la pregunta:", type(error).__name__)
            print("Detalle técnico:", error)
            raise SystemExit(1)
        # Fuentes que el modelo tuvo disponibles, respuesta y la traducción
        # de cada [N] citado a su archivo.
        print("Fuentes recuperadas:", citas)
        print("Respuesta:", respuesta)
        print("Citas de la respuesta:", resolver_citas(respuesta, citas))