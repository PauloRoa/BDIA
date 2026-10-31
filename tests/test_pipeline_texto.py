import pytest

from pipeline_texto import calcular_coincidencia, limpiar_texto, procesar_texto


def test_procesar_texto_normaliza_mayusculas_y_puntuacion():
    resultado = procesar_texto("El Cielo, es AZUL!")
    assert resultado == ["el", "cielo", "es", "azul"]


def test_procesar_texto_solo_puntuacion_devuelve_lista_vacia():
    resultado = procesar_texto("¡¡¡...!!!")
    assert resultado == []


def test_limpiar_texto_rechaza_entrada_que_no_es_texto():
    with pytest.raises(TypeError):
        limpiar_texto(None)


def test_calcular_coincidencia_texto_procesado():
    tokens_referencia = procesar_texto("El cielo es azul.")
    tokens_respuesta = procesar_texto("el cielo es azul")
    assert calcular_coincidencia(tokens_referencia, tokens_respuesta) == 1.0


def test_calcular_coincidencia_referencia_vacia_devuelve_cero():
    assert calcular_coincidencia([], ["el", "cielo"]) == 0.0