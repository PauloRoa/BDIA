import logging
import os

from dotenv import load_dotenv
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from consumir_gemini import MODELO
from enrutamiento import (
    MENSAJE_ERROR_CONFIGURACION,
    MENSAJE_ERROR_GENERAL,
    es_error_de_configuracion,
)

logger = logging.getLogger(__name__)

BUENAS_PRACTICAS = {
    "clave primaria": (
        "Cada tabla tiene una clave primaria que identifica cada fila de forma "
        "única y que no cambia en el tiempo."
    ),
    "clave foránea": (
        "Una clave foránea referencia la clave primaria de otra tabla y asegura "
        "que cada relación apunte a una fila que existe."
    ),
    "muchos a muchos": (
        "Una relación muchos a muchos se resuelve con una tabla intermedia que "
        "guarda las claves foráneas de las dos tablas relacionadas."
    ),
    "normalización": (
        "Cada dato se guarda en un solo lugar: no se repiten datos ni se "
        "almacenan columnas que se pueden calcular a partir de otras tablas."
    ),
    "tipo de dato": (
        "Cada columna usa el tipo más ajustado a su contenido: numeric para "
        "montos, integer para cantidades y timestamp para fechas con hora."
    ),
}

SENTENCIAS_PERMITIDAS = ("CREATE TABLE", "CREATE INDEX")


@tool
def consultar_buenas_practicas(tema: str) -> str:
    """Devuelve la buena práctica de modelado de bases de datos relacionales
    sobre un tema, como clave primaria, clave foránea, muchos a muchos,
    normalización o tipo de dato. Usar cuando el usuario pregunta cómo o por
    qué se modela algo de cierta forma."""
    for clave, practica in BUENAS_PRACTICAS.items():
        if clave in tema.lower():
            return practica
    return "No hay una buena práctica registrada para ese tema."


@tool
def verificar_sentencias_permitidas(script: str) -> str:
    """Revisa si un script SQL usa solo las sentencias que el servicio permite:
    CREATE TABLE y CREATE INDEX. Usar cuando el usuario entrega un script SQL
    y pregunta si cumple las reglas del servicio."""
    sentencias = [sentencia.strip() for sentencia in script.split(";")]
    sentencias = [sentencia for sentencia in sentencias if sentencia]
    if not sentencias:
        return "El script no contiene sentencias."
    no_permitidas = [
        sentencia
        for sentencia in sentencias
        if not sentencia.upper().startswith(SENTENCIAS_PERMITIDAS)
    ]
    if no_permitidas:
        return "El script contiene sentencias no permitidas: " + "; ".join(
            no_permitidas
        )
    return f"El script cumple: sus {len(sentencias)} sentencias están permitidas."


HERRAMIENTAS = [consultar_buenas_practicas, verificar_sentencias_permitidas]

PROMPT_AGENTE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Eres un asistente de diseño de bases de datos relacionales en "
            "PostgreSQL. Usa las herramientas disponibles cuando las necesites "
            "y apóyate en lo que devuelven. Responde en español, en no más de "
            "tres oraciones y sin formato markdown.",
        ),
        ("human", "{entrada}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)


def construir_agente(modelo):
    agente = create_tool_calling_agent(modelo, HERRAMIENTAS, PROMPT_AGENTE)
    return AgentExecutor(
        agent=agente,
        tools=HERRAMIENTAS,
        verbose=True,
        return_intermediate_steps=True,
    )


def herramientas_usadas(resultado):
    return [accion.tool for accion, observacion in resultado["intermediate_steps"]]


def texto_de_salida(salida):
    if isinstance(salida, str):
        return salida
    return "".join(bloque["text"] for bloque in salida if bloque.get("type") == "text")


def consultar_agente_seguro(ejecutor_agente, entrada):
    try:
        resultado = ejecutor_agente.invoke({"entrada": entrada})
    except Exception as error:
        logger.exception("Error consultando al agente")
        if es_error_de_configuracion(error):
            return MENSAJE_ERROR_CONFIGURACION, None
        return MENSAJE_ERROR_GENERAL, None
    return texto_de_salida(resultado["output"]), herramientas_usadas(resultado)


VERIFICACIONES = [
    (
        "¿Por qué una relación muchos a muchos necesita una tabla intermedia?",
        "consultar_buenas_practicas",
    ),
    (
        "¿Este script cumple las sentencias permitidas? "
        "CREATE TABLE cliente (id serial PRIMARY KEY); DROP TABLE venta;",
        "verificar_sentencias_permitidas",
    ),
    ("¿Qué es PostgreSQL?", None),
]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    modelo = ChatGoogleGenerativeAI(
        model=MODELO,
        google_api_key=os.getenv("API_KEY"),
        temperature=0,
        timeout=60,
    )
    ejecutor_agente = construir_agente(modelo)

    for entrada, herramienta_esperada in VERIFICACIONES:
        respuesta, herramientas = consultar_agente_seguro(ejecutor_agente, entrada)
        print(f"Entrada: {entrada}")
        print(f"Respuesta: {respuesta}")
        if herramientas is None:
            print("Verificación no realizada: la consulta falló.\n")
            continue
        print(f"Herramientas usadas: {herramientas}\n")
        if herramienta_esperada is None:
            assert herramientas == []
        else:
            assert herramienta_esperada in herramientas