from unittest.mock import MagicMock

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from enrutamiento import (
    MENSAJE_ERROR_CONFIGURACION,
    MENSAJE_ERROR_GENERAL,
    MENSAJE_RESPALDO_ACLARACION,
    MENSAJE_RESPALDO_NUEVA,
    construir_cadena_con_enrutamiento,
    construir_paso_clasificacion,
    construir_ruta_segura,
    procesar_solicitud_segura,
)

ENTRADA = {"descripcion": "Una tienda vende productos a clientes."}


def fallar_a_proposito(entrada):
    raise ConnectionError("error de red simulado")


def crear_clasificacion_falsa(categoria):
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.return_value = categoria
    return clasificacion_falsa


def test_ruta_segura_usa_respaldo_ante_fallo_del_modelo():
    ruta_segura = construir_ruta_segura(
        RunnableLambda(fallar_a_proposito), MENSAJE_RESPALDO_NUEVA
    )

    resultado = ruta_segura.invoke(ENTRADA)

    assert resultado == MENSAJE_RESPALDO_NUEVA


def test_ruta_segura_no_usa_respaldo_si_la_ruta_funciona():
    ruta_segura = construir_ruta_segura(
        RunnableLambda(lambda entrada: "CREATE TABLE producto (id serial PRIMARY KEY);"),
        MENSAJE_RESPALDO_NUEVA,
    )

    resultado = ruta_segura.invoke(ENTRADA)

    assert resultado == "CREATE TABLE producto (id serial PRIMARY KEY);"


def test_flujo_completo_entrega_respaldo_si_falla_la_ruta_nueva():
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=crear_clasificacion_falsa("nueva"),
        cadena_nueva=construir_ruta_segura(
            RunnableLambda(fallar_a_proposito), MENSAJE_RESPALDO_NUEVA
        ),
    )

    resultado = procesar_solicitud_segura(cadena, ENTRADA["descripcion"])

    assert resultado == MENSAJE_RESPALDO_NUEVA


def test_procesar_solicitud_segura_no_propaga_fallo_de_la_clasificacion():
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.side_effect = ConnectionError("error de red simulado")
    cadena = construir_cadena_con_enrutamiento(paso_clasificacion=clasificacion_falsa)

    resultado = procesar_solicitud_segura(cadena, ENTRADA["descripcion"])

    assert resultado == MENSAJE_ERROR_GENERAL


def test_procesar_solicitud_segura_devuelve_el_resultado_normal():
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=crear_clasificacion_falsa("nueva"),
        cadena_nueva=RunnableLambda(lambda entrada: "script generado"),
    )

    resultado = procesar_solicitud_segura(cadena, ENTRADA["descripcion"])

    assert resultado == "script generado"


def test_clasificacion_vacia_cae_en_aclaracion():
    modelo_falso = MagicMock()
    modelo_falso.return_value = AIMessage(content="   ")
    cadena_aclaracion = RunnableLambda(lambda entrada: "respuesta de aclaración")
    cadena_nueva_falsa = MagicMock()
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=construir_paso_clasificacion(modelo_falso),
        cadena_nueva=cadena_nueva_falsa,
        cadena_aclaracion=cadena_aclaracion,
    )

    resultado = cadena.invoke({"descripcion": ""})

    assert resultado == "respuesta de aclaración"
    assert not cadena_nueva_falsa.called


def test_procesar_solicitud_segura_distingue_error_de_configuracion():
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.side_effect = Exception(
        "400 INVALID_ARGUMENT. {'reason': 'API_KEY_INVALID'}"
    )
    cadena = construir_cadena_con_enrutamiento(paso_clasificacion=clasificacion_falsa)

    resultado = procesar_solicitud_segura(cadena, ENTRADA["descripcion"])

    assert resultado == MENSAJE_ERROR_CONFIGURACION


def test_procesar_solicitud_segura_no_llama_al_modelo_con_entrada_vacia():
    clasificacion_falsa = MagicMock()
    cadena = construir_cadena_con_enrutamiento(paso_clasificacion=clasificacion_falsa)

    resultado = procesar_solicitud_segura(cadena, "   ")

    assert resultado == MENSAJE_RESPALDO_ACLARACION
    assert not clasificacion_falsa.called


def test_procesar_solicitud_segura_no_se_cae_con_entrada_que_no_es_texto():
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=crear_clasificacion_falsa("nueva"),
    )

    resultado = procesar_solicitud_segura(cadena, None)

    assert resultado == MENSAJE_ERROR_GENERAL