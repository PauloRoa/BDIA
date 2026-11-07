from unittest.mock import MagicMock

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from enrutamiento import (
    construir_cadena_con_enrutamiento,
    construir_paso_clasificacion,
)

ENTRADA = {"descripcion": "Una tienda vende productos a clientes."}


def crear_clasificacion_falsa(categoria):
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.return_value = categoria
    return clasificacion_falsa


def crear_ruta_falsa(respuesta):
    ruta_falsa = MagicMock()
    ruta_falsa.return_value = respuesta
    return ruta_falsa


def test_enrutamiento_va_a_cadena_nueva():
    cadena_nueva_falsa = crear_ruta_falsa("CREATE TABLE producto (id serial PRIMARY KEY);")
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=crear_clasificacion_falsa("nueva"),
        cadena_nueva=cadena_nueva_falsa,
    )

    resultado = cadena.invoke(ENTRADA)

    assert cadena_nueva_falsa.called
    assert resultado == "CREATE TABLE producto (id serial PRIMARY KEY);"


def test_cadena_nueva_recibe_la_descripcion_original():
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=crear_clasificacion_falsa("nueva"),
        cadena_nueva=RunnableLambda(lambda entrada: entrada["descripcion"]),
    )

    resultado = cadena.invoke(ENTRADA)

    assert resultado == ENTRADA["descripcion"]


def test_enrutamiento_va_a_cadena_existente():
    cadena_existente_falsa = crear_ruta_falsa("respuesta de rechazo")
    cadena_nueva_falsa = crear_ruta_falsa("no debería ejecutarse")
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=crear_clasificacion_falsa("existente"),
        cadena_nueva=cadena_nueva_falsa,
        cadena_existente=cadena_existente_falsa,
    )

    resultado = cadena.invoke(ENTRADA)

    assert cadena_existente_falsa.called
    assert not cadena_nueva_falsa.called
    assert resultado == "respuesta de rechazo"


def test_enrutamiento_usa_aclaracion_ante_categoria_otra():
    cadena_aclaracion_falsa = crear_ruta_falsa("respuesta de aclaración")
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=crear_clasificacion_falsa("otra"),
        cadena_aclaracion=cadena_aclaracion_falsa,
    )

    resultado = cadena.invoke(ENTRADA)

    assert cadena_aclaracion_falsa.called
    assert resultado == "respuesta de aclaración"


def test_enrutamiento_usa_aclaracion_ante_categoria_inesperada():
    cadena_aclaracion_falsa = crear_ruta_falsa("respuesta de aclaración")
    cadena_nueva_falsa = crear_ruta_falsa("no debería ejecutarse")
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=crear_clasificacion_falsa("no estoy seguro"),
        cadena_nueva=cadena_nueva_falsa,
        cadena_aclaracion=cadena_aclaracion_falsa,
    )

    resultado = cadena.invoke(ENTRADA)

    assert cadena_aclaracion_falsa.called
    assert not cadena_nueva_falsa.called
    assert resultado == "respuesta de aclaración"


def test_clasificacion_normaliza_antes_de_comparar():
    modelo_falso = MagicMock()
    modelo_falso.return_value = AIMessage(content=" Nueva \n")

    resultado = construir_paso_clasificacion(modelo_falso).invoke(ENTRADA)

    assert resultado == "nueva"


def test_clasificacion_ignora_puntuacion_y_formato():
    for respuesta_modelo in ["Nueva.", "**nueva**", " NUEVA \n"]:
        modelo_falso = MagicMock()
        modelo_falso.return_value = AIMessage(content=respuesta_modelo)

        resultado = construir_paso_clasificacion(modelo_falso).invoke(ENTRADA)

        assert resultado == "nueva"