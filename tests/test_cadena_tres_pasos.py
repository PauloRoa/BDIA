from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from cadena_tres_pasos import construir_cadena

DESCRIPCION = "Una tienda vende productos a clientes."
SALIDA_EXTRAER = "Entidad Producto; entidad Cliente; Cliente compra Producto (muchos a muchos)"
SALIDA_MODELAR = "Tabla producto; tabla cliente; tabla intermedia venta_producto"
SALIDA_GENERAR = "CREATE TABLE producto (id serial PRIMARY KEY);"


def crear_modelo_falso():
    modelo_falso = MagicMock()
    modelo_falso.side_effect = [
        AIMessage(content=SALIDA_EXTRAER),
        AIMessage(content=SALIDA_MODELAR),
        AIMessage(content=SALIDA_GENERAR),
    ]
    return modelo_falso


def test_cadena_hace_tres_llamadas_y_devuelve_el_script():
    modelo_falso = crear_modelo_falso()
    cadena = construir_cadena(modelo_falso)

    resultado = cadena.invoke({"descripcion": DESCRIPCION})

    assert modelo_falso.call_count == 3
    assert resultado == SALIDA_GENERAR
    assert isinstance(resultado, str)


def test_cada_paso_recibe_la_salida_del_anterior():
    modelo_eco = RunnableLambda(lambda prompt: AIMessage(content=prompt.text))
    cadena = construir_cadena(modelo_eco)

    resultado = cadena.invoke({"descripcion": DESCRIPCION})

    assert "Tablas:" in resultado
    assert "Entidades y relaciones:" in resultado
    assert DESCRIPCION in resultado


def test_variable_de_entrada_incorrecta_falla_antes_de_llamar_al_modelo():
    modelo_falso = crear_modelo_falso()
    cadena = construir_cadena(modelo_falso)

    with pytest.raises(KeyError):
        cadena.invoke({"texto": DESCRIPCION})

    assert modelo_falso.call_count == 0