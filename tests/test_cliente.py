from unittest.mock import Mock, patch

import pytest

import cliente
from cliente import con_reintento, consultar_modelo, registrar_costo
from consumir_gemini import enviar_peticion

URL = "https://ejemplo.test/modelo:generateContent"
HEADERS = {"x-goog-api-key": "clave-de-prueba"}
BODY = {"contents": [{"parts": [{"text": "test"}]}]}


@pytest.fixture(autouse=True)
def reiniciar_costo_total():
    cliente.costo_total_sesion = 0.0
    yield


# enviar_peticion

def test_enviar_peticion_credencial_invalida():
    respuesta_falsa = Mock(status_code=401)
    with patch("consumir_gemini.requests.post", return_value=respuesta_falsa):
        with pytest.raises(ValueError):
            enviar_peticion(URL, HEADERS, BODY)


def test_enviar_peticion_sin_permiso():
    respuesta_falsa = Mock(status_code=403)
    with patch("consumir_gemini.requests.post", return_value=respuesta_falsa):
        with pytest.raises(ValueError):
            enviar_peticion(URL, HEADERS, BODY)


def test_enviar_peticion_clave_invalida_gemini():
    respuesta_falsa = Mock(status_code=400)
    respuesta_falsa.json.return_value = {
        "error": {
            "message": "API key not valid. Please pass a valid API key.",
            "details": [{"reason": "API_KEY_INVALID"}],
        }
    }
    with patch("consumir_gemini.requests.post", return_value=respuesta_falsa):
        with pytest.raises(ValueError):
            enviar_peticion(URL, HEADERS, BODY)


def test_enviar_peticion_limite_de_uso():
    respuesta_falsa = Mock(status_code=429)
    with patch("consumir_gemini.requests.post", return_value=respuesta_falsa):
        with pytest.raises(TimeoutError):
            enviar_peticion(URL, HEADERS, BODY)


def test_enviar_peticion_falla_del_proveedor():
    respuesta_falsa = Mock(status_code=503)
    with patch("consumir_gemini.requests.post", return_value=respuesta_falsa):
        with pytest.raises(TimeoutError):
            enviar_peticion(URL, HEADERS, BODY)


def test_enviar_peticion_exito():
    respuesta_json = {"candidates": [{"content": {"parts": [{"text": "respuesta simulada"}]}}]}
    respuesta_falsa = Mock(status_code=200)
    respuesta_falsa.json.return_value = respuesta_json
    with patch("consumir_gemini.requests.post", return_value=respuesta_falsa):
        resultado = enviar_peticion(URL, HEADERS, BODY)
    assert resultado == respuesta_json


# con_reintento

def test_con_reintento_espera_entre_intentos():
    intentos = {"n": 0}

    def funcion_que_falla_una_vez():
        intentos["n"] += 1
        if intentos["n"] == 1:
            raise TimeoutError("simulado")
        return "ok"

    with patch("cliente.time.sleep") as mock_sleep:
        resultado = con_reintento(funcion_que_falla_una_vez)
    assert resultado == "ok"
    mock_sleep.assert_called_once()


def test_con_reintento_no_reintenta_value_error():
    intentos = {"n": 0}

    def funcion_con_error_de_credencial():
        intentos["n"] += 1
        raise ValueError("simulado")

    with patch("cliente.time.sleep") as mock_sleep:
        with pytest.raises(ValueError):
            con_reintento(funcion_con_error_de_credencial)
    assert intentos["n"] == 1
    mock_sleep.assert_not_called()


def test_con_reintento_agota_intentos():
    intentos = {"n": 0}

    def siempre_falla():
        intentos["n"] += 1
        raise TimeoutError("simulado")

    with patch("cliente.time.sleep"):
        with pytest.raises(TimeoutError):
            con_reintento(siempre_falla, intentos=3)
    assert intentos["n"] == 3


# registrar_costo

def test_registrar_costo_calcula_costo():
    respuesta_falsa = {"usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 1000, "totalTokenCount": 2000}}
    costo = registrar_costo(respuesta_falsa)
    assert costo == pytest.approx(1000 * cliente.PRECIO_ENTRADA + 1000 * cliente.PRECIO_SALIDA)


def test_registrar_costo_acumula():
    respuesta_falsa = {"usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 1000, "totalTokenCount": 2000}}
    costo = registrar_costo(respuesta_falsa)
    registrar_costo(respuesta_falsa)
    assert cliente.costo_total_sesion == pytest.approx(2 * costo)


# consultar_modelo

def test_consultar_modelo_convierte_error():
    with patch("cliente.con_reintento", side_effect=TimeoutError("simulado")):
        with pytest.raises(RuntimeError):
            consultar_modelo("pregunta de prueba")


def test_consultar_modelo_propaga_value_error():
    with patch("cliente.con_reintento", side_effect=ValueError("Credencial inválida o sin permiso. Revisa tu API_KEY.")):
        with pytest.raises(ValueError):
            consultar_modelo("pregunta de prueba")