import pytest

from pipeline_texto import (
    calcular_coincidencia,
    calcular_metricas,
    calcular_precision_cobertura_f1,
    limpiar_texto,
    procesar_texto,
)


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


def test_calcular_precision_cobertura_f1_ejemplo_calculado_a_mano():
    tokens_referencia = procesar_texto("El gato duerme en el sofá.")
    tokens_respuesta = procesar_texto("El gato duerme en el sillón todo el día.")
    resultado = calcular_precision_cobertura_f1(tokens_referencia, tokens_respuesta)
    assert resultado["precision"] == pytest.approx(5 / 9)
    assert resultado["cobertura"] == pytest.approx(5 / 6)
    assert resultado["f1"] == pytest.approx(2 / 3)


def test_metrica_no_detecta_dato_incorrecto():
    resultado = calcular_metricas("El tipo INTEGER ocupa 4 bytes en PostgreSQL.", "El tipo INTEGER ocupa 8 bytes en PostgreSQL.")
    assert resultado["f1"] == pytest.approx(0.875)


def test_metrica_no_detecta_negacion_ausente():
    resultado = calcular_metricas("Una clave primaria no puede contener valores nulos.", "Una clave primaria puede contener valores nulos.")
    assert resultado["f1"] == pytest.approx(14 / 15)