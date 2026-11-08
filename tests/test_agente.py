from unittest.mock import MagicMock

import pytest
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError

from agente_con_herramientas import (
    consultar_agente_seguro,
    consultar_buenas_practicas,
    texto_de_salida,
    verificar_sentencias_permitidas,
)
from agente_con_memoria import (
    agregar_memoria,
    cerrar_sesion,
    historiales,
    obtener_historial,
)
from enrutamiento import MENSAJE_ERROR_GENERAL


def test_consultar_buenas_practicas_sin_ejemplo():
    resultado = consultar_buenas_practicas.invoke({"tema": "muchos a muchos"})

    assert "tabla intermedia" in resultado
    assert "Ejemplo:" not in resultado


def test_consultar_buenas_practicas_con_ejemplo():
    resultado = consultar_buenas_practicas.invoke(
        {"tema": "muchos a muchos", "incluir_ejemplo": True}
    )

    assert "tabla intermedia" in resultado
    assert "Ejemplo:" in resultado


def test_consultar_buenas_practicas_tema_desconocido():
    resultado = consultar_buenas_practicas.invoke({"tema": "particionamiento"})

    assert resultado == "No hay una buena práctica registrada para ese tema."


def test_consultar_buenas_practicas_rechaza_argumento_invalido():
    with pytest.raises(ValidationError):
        consultar_buenas_practicas.invoke(
            {"tema": "muchos a muchos", "incluir_ejemplo": "tal vez"}
        )


def test_verificar_sentencias_permitidas_detecta_sentencia_no_permitida():
    resultado = verificar_sentencias_permitidas.invoke(
        "CREATE TABLE cliente (id serial PRIMARY KEY); DROP TABLE venta;"
    )

    assert resultado == "El script contiene sentencias no permitidas: DROP TABLE venta"


def test_verificar_sentencias_permitidas_acepta_create_table_e_index():
    resultado = verificar_sentencias_permitidas.invoke(
        "create table cliente (id serial PRIMARY KEY); "
        "CREATE INDEX idx_cliente ON cliente (id);"
    )

    assert resultado == "El script cumple: sus 2 sentencias están permitidas."


def test_verificar_sentencias_permitidas_script_vacio():
    resultado = verificar_sentencias_permitidas.invoke("  ;  ")

    assert resultado == "El script no contiene sentencias."


def test_texto_de_salida_une_los_bloques_de_texto():
    salida = [
        {"type": "text", "text": "Hola, ", "extras": {}},
        {"type": "text", "text": "mundo."},
    ]

    assert texto_de_salida(salida) == "Hola, mundo."
    assert texto_de_salida("texto simple") == "texto simple"


def test_consultar_agente_seguro_no_propaga_fallo_de_conexion():
    ejecutor_falso = MagicMock()
    ejecutor_falso.invoke.side_effect = ConnectionError("conexión interrumpida")

    respuesta, herramientas = consultar_agente_seguro(ejecutor_falso, "pregunta")

    assert respuesta == MENSAJE_ERROR_GENERAL
    assert herramientas is None


def test_obtener_historial_separa_sesiones():
    historial_1 = obtener_historial("prueba_sesion_1")
    historial_2 = obtener_historial("prueba_sesion_2")
    historial_1.add_user_message("mensaje solo de la sesión 1")

    assert len(obtener_historial("prueba_sesion_1").messages) == 1
    assert len(historial_2.messages) == 0

    cerrar_sesion("prueba_sesion_1")
    cerrar_sesion("prueba_sesion_2")


def test_cerrar_sesion_elimina_el_historial_y_no_falla_si_no_existe():
    obtener_historial("prueba_cierre")

    cerrar_sesion("prueba_cierre")
    cerrar_sesion("prueba_cierre")

    assert "prueba_cierre" not in historiales


def test_agregar_memoria_guarda_la_respuesta_en_bloques_como_texto():
    def agente_falso(entrada):
        return {
            "output": [{"type": "text", "text": "respuesta del agente", "extras": {}}],
            "intermediate_steps": [],
        }

    agente_con_memoria = agregar_memoria(RunnableLambda(agente_falso))
    config = {"configurable": {"session_id": "prueba_bloques"}}

    agente_con_memoria.invoke({"entrada": "primera pregunta"}, config)
    resultado = agente_con_memoria.invoke({"entrada": "segunda pregunta"}, config)

    mensajes = obtener_historial("prueba_bloques").messages
    assert resultado["output"] == "respuesta del agente"
    assert len(mensajes) == 4
    assert mensajes[1].content == "respuesta del agente"

    cerrar_sesion("prueba_bloques")