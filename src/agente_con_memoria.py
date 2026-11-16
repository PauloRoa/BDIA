import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_google_genai import ChatGoogleGenerativeAI

from agente_con_herramientas import (
    INSTRUCCION_SISTEMA,
    construir_agente,
    registro_aprobaciones,
    texto_de_salida
)
from consumir_gemini import MODELO
from enrutamiento import (
    MENSAJE_ERROR_CONFIGURACION,
    MENSAJE_ERROR_GENERAL,
    es_error_de_configuracion,
)

logger = logging.getLogger(__name__)

ARCHIVO_TRAZAS = Path(__file__).resolve().parents[1] / "docs" / "trazas_agente.jsonl"

PROMPT_AGENTE_CON_MEMORIA = ChatPromptTemplate.from_messages(
    [
        ("system", INSTRUCCION_SISTEMA),
        MessagesPlaceholder("chat_history"),
        ("human", "{entrada}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)

historiales = {}


def obtener_historial(session_id: str):
    if session_id not in historiales:
        historiales[session_id] = InMemoryChatMessageHistory()
    return historiales[session_id]


def cerrar_sesion(session_id: str):
    historiales.pop(session_id, None)


def salida_como_texto(resultado):
    return {**resultado, "output": texto_de_salida(resultado["output"])}


def agregar_memoria(ejecutor_agente):
    return RunnableWithMessageHistory(
        ejecutor_agente | RunnableLambda(salida_como_texto),
        obtener_historial,
        input_messages_key="entrada",
        history_messages_key="chat_history",
    )


def construir_agente_con_memoria(modelo):
    return agregar_memoria(construir_agente(modelo, PROMPT_AGENTE_CON_MEMORIA))


def registrar_traza(
    session_id: str,
    entrada: str,
    resultado: dict,
    archivo: Path = ARCHIVO_TRAZAS,
) -> None:
    """Guarda una interacción del agente como una línea JSON: qué se preguntó,
    qué herramientas se usaron y con qué argumentos, y la respuesta final. Si
    "resultado" no trae "intermediate_steps", acciones queda como lista vacía."""
    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "entrada": entrada,
        "acciones": [
            {
                "herramienta": accion.tool,
                "argumentos": accion.tool_input,
                "observacion": observacion,
            }
            for accion, observacion in resultado.get("intermediate_steps", [])
        ],
        "respuesta_final": resultado["output"],
    }
    with open(archivo, "a", encoding="utf-8") as salida:
        salida.write(json.dumps(registro, ensure_ascii=False) + "\n")


def consultar_con_memoria_seguro(agente_con_memoria, entrada, session_id):
    config = {"configurable": {"session_id": session_id}}
    try:
        resultado = agente_con_memoria.invoke({"entrada": entrada}, config)
    except Exception as error:
        logger.exception("Error consultando al agente con memoria")
        if es_error_de_configuracion(error):
            return MENSAJE_ERROR_CONFIGURACION, None
        return MENSAJE_ERROR_GENERAL, None
    pasos = [
        (accion.tool, accion.tool_input)
        for accion, observacion in resultado["intermediate_steps"]
    ]
    try:
        registrar_traza(session_id, entrada, resultado)
    except Exception:
        logger.exception("No se pudo registrar la traza")
    return resultado["output"], pasos


def mostrar_turno(session_id, entrada, respuesta, pasos):
    print(f"Sesión: {session_id}")
    print(f"Entrada: {entrada}")
    print(f"Respuesta: {respuesta}")
    print(f"Herramientas llamadas: {pasos}")
    print(f"Mensajes en el historial: {len(obtener_historial(session_id).messages)}\n")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    modelo = ChatGoogleGenerativeAI(
        model=MODELO,
        google_api_key=os.getenv("API_KEY"),
        temperature=0,
        timeout=60,
    )
    agente_con_memoria = construir_agente_con_memoria(modelo)

    # Una entrada por nivel de riesgo. Las dos últimas llegan a la herramienta
    # de riesgo alto y piden aprobación humana: responder "s" y luego "n".
    sesion = "supervision_riesgos"
    script = "CREATE TABLE cliente (id serial PRIMARY KEY, nombre text);"
    entradas = [
        "¿Cómo se resuelve una relación muchos a muchos?",
        f"Verifica si este script solo usa sentencias permitidas: {script}",
        f"Guarda como borrador con el nombre ferreteria_demo este script: {script}",
        f"Guarda como borrador con el nombre ferreteria_rechazo este script: {script}",
    ]
    for entrada in entradas:
        respuesta, pasos = consultar_con_memoria_seguro(
            agente_con_memoria, entrada, sesion
        )
        mostrar_turno(sesion, entrada, respuesta, pasos)

    print(f"Decisiones de aprobación registradas: {registro_aprobaciones}")
    cerrar_sesion(sesion)