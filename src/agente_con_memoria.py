import logging
import os

from dotenv import load_dotenv
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_google_genai import ChatGoogleGenerativeAI

from agente_con_herramientas import (
    INSTRUCCION_SISTEMA,
    construir_agente,
    texto_de_salida,
)
from consumir_gemini import MODELO
from enrutamiento import (
    MENSAJE_ERROR_CONFIGURACION,
    MENSAJE_ERROR_GENERAL,
    es_error_de_configuracion,
)

logger = logging.getLogger(__name__)

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

    # Verificación 1: el segundo turno usa lo que se dijo en el primero.
    sesion = "verificacion_dos_turnos"
    turnos = [
        "¿Cómo se resuelve una relación muchos a muchos?",
        "¿Me das un ejemplo de eso?",
    ]
    for numero, entrada in enumerate(turnos, start=1):
        respuesta, pasos = consultar_con_memoria_seguro(
            agente_con_memoria, entrada, sesion
        )
        mostrar_turno(sesion, entrada, respuesta, pasos)
        if pasos is None:
            print("Verificación no realizada: la consulta falló.\n")
            break
        assert len(obtener_historial(sesion).messages) == numero * 2

    # Verificación 2: dos sesiones distintas no comparten historial.
    conversaciones = [
        ("cliente_1", "Estoy preguntando por la relación entre venta y producto."),
        ("cliente_2", "¿Por qué relación te pregunté?"),
    ]
    for sesion_cliente, entrada in conversaciones:
        respuesta, pasos = consultar_con_memoria_seguro(
            agente_con_memoria, entrada, sesion_cliente
        )
        mostrar_turno(sesion_cliente, entrada, respuesta, pasos)
        if pasos is None:
            print("Verificación no realizada: la consulta falló.\n")
            continue
        assert len(obtener_historial(sesion_cliente).messages) == 2

    for sesion_usada in [sesion, "cliente_1", "cliente_2"]:
        cerrar_sesion(sesion_usada)
    assert historiales == {}