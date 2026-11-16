import json
import time
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from langchain_core.agents import AgentAction
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError

from agente_con_herramientas import (
    consultar_agente_seguro,
    consultar_buenas_practicas,
    esperar_aprobacion,
    guardar_borrador,
    registro_aprobaciones,
    texto_de_salida,
    verificar_sentencias_permitidas,
)
from agente_con_memoria import (
    agregar_memoria,
    cerrar_sesion,
    consultar_con_memoria_seguro,
    historiales,
    obtener_historial,
    registrar_traza,
)
from enrutamiento import MENSAJE_ERROR_GENERAL

SCRIPT_VALIDO = "CREATE TABLE cliente (id serial PRIMARY KEY);"
ARCHIVO_TRAZA_PRUEBA = Path(__file__).parent / "traza_prueba.jsonl"


@pytest.fixture(autouse=True)
def reiniciar_estado():
    registro_aprobaciones.clear()
    if ARCHIVO_TRAZA_PRUEBA.exists():
        ARCHIVO_TRAZA_PRUEBA.unlink()


def carpeta_falsa(existe):
    carpeta = MagicMock()
    carpeta.__truediv__.return_value.exists.return_value = existe
    return carpeta


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


def test_guardar_borrador_aprobado_crea_el_archivo_y_registra_la_decision():
    abrir = mock_open()
    with patch("agente_con_herramientas.CARPETA_BORRADORES", carpeta_falsa(False)), \
            patch("agente_con_herramientas.esperar_aprobacion", return_value=True), \
            patch("agente_con_herramientas.open", abrir, create=True):
        resultado = guardar_borrador.invoke(
            {"nombre": "ferreteria", "script": SCRIPT_VALIDO}
        )

    assert "aprobado por el supervisor humano" in resultado
    assert "se creó" in resultado
    assert abrir().write.call_count == 1
    assert len(registro_aprobaciones) == 1
    assert registro_aprobaciones[0]["herramienta"] == "guardar_borrador"
    assert registro_aprobaciones[0]["aprobado"] is True
    assert registro_aprobaciones[0]["argumentos"]["reemplaza"] is False


def test_guardar_borrador_aprobado_reemplaza_un_borrador_existente():
    abrir = mock_open()
    with patch("agente_con_herramientas.CARPETA_BORRADORES", carpeta_falsa(True)), \
            patch("agente_con_herramientas.esperar_aprobacion", return_value=True), \
            patch("agente_con_herramientas.open", abrir, create=True):
        resultado = guardar_borrador.invoke(
            {"nombre": "ferreteria", "script": SCRIPT_VALIDO}
        )

    assert "se reemplazó" in resultado
    assert abrir().write.call_count == 1
    assert registro_aprobaciones[0]["argumentos"]["reemplaza"] is True


def test_guardar_borrador_rechazado_no_escribe_y_registra_el_rechazo():
    abrir = mock_open()
    with patch("agente_con_herramientas.CARPETA_BORRADORES", carpeta_falsa(False)), \
            patch("agente_con_herramientas.esperar_aprobacion", return_value=False), \
            patch("agente_con_herramientas.open", abrir, create=True):
        resultado = guardar_borrador.invoke(
            {"nombre": "ferreteria", "script": SCRIPT_VALIDO}
        )

    assert "rechazado" in resultado
    assert abrir.call_count == 0
    assert len(registro_aprobaciones) == 1
    assert registro_aprobaciones[0]["aprobado"] is False


def test_guardar_borrador_sentencia_no_permitida_no_pide_aprobacion():
    aprobacion = MagicMock(return_value=True)
    abrir = mock_open()
    with patch("agente_con_herramientas.CARPETA_BORRADORES", carpeta_falsa(False)), \
            patch("agente_con_herramientas.esperar_aprobacion", aprobacion), \
            patch("agente_con_herramientas.open", abrir, create=True):
        resultado = guardar_borrador.invoke(
            {"nombre": "ferreteria", "script": SCRIPT_VALIDO + " DROP TABLE venta;"}
        )

    assert "sentencias no permitidas" in resultado
    assert "DROP TABLE venta" in resultado
    assert aprobacion.call_count == 0
    assert abrir.call_count == 0
    assert registro_aprobaciones == []


def test_guardar_borrador_nombre_invalido_no_pide_aprobacion():
    aprobacion = MagicMock(return_value=True)
    abrir = mock_open()
    with patch("agente_con_herramientas.CARPETA_BORRADORES", carpeta_falsa(False)), \
            patch("agente_con_herramientas.esperar_aprobacion", aprobacion), \
            patch("agente_con_herramientas.open", abrir, create=True):
        resultado = guardar_borrador.invoke(
            {"nombre": "../../fuera", "script": SCRIPT_VALIDO}
        )

    assert "el nombre solo puede tener" in resultado
    assert aprobacion.call_count == 0
    assert abrir.call_count == 0


def test_esperar_aprobacion_acepta_solo_la_respuesta_s():
    with patch("builtins.input", return_value=" S "):
        assert esperar_aprobacion("¿Aprobar? ") is True
    with patch("builtins.input", return_value="n"):
        assert esperar_aprobacion("¿Aprobar? ") is False
    with patch("builtins.input", return_value="sí"):
        assert esperar_aprobacion("¿Aprobar? ") is False


def test_esperar_aprobacion_rechaza_si_no_hay_entrada_disponible():
    with patch("builtins.input", side_effect=EOFError):
        assert esperar_aprobacion("¿Aprobar? ") is False


def test_esperar_aprobacion_rechaza_al_agotarse_el_tiempo():
    def respuesta_tardia(mensaje):
        time.sleep(0.5)
        return "s"

    with patch("builtins.input", side_effect=respuesta_tardia):
        assert esperar_aprobacion("¿Aprobar? ", tiempo_limite_segundos=0.05) is False


def test_registrar_traza_guarda_una_linea_con_herramienta_argumentos_y_respuesta():
    accion = AgentAction("consultar_buenas_practicas", {"tema": "ñandú"}, "registro")
    resultado = {
        "output": "Respuesta con acentos: á",
        "intermediate_steps": [(accion, "observación de la herramienta")],
    }

    registrar_traza("cliente_1", "¿Qué es una clave?", resultado, ARCHIVO_TRAZA_PRUEBA)

    lineas = ARCHIVO_TRAZA_PRUEBA.read_text(encoding="utf-8").splitlines()
    registro = json.loads(lineas[0])
    assert len(lineas) == 1
    assert registro["session_id"] == "cliente_1"
    assert registro["entrada"] == "¿Qué es una clave?"
    assert registro["acciones"][0]["herramienta"] == "consultar_buenas_practicas"
    assert registro["acciones"][0]["argumentos"] == {"tema": "ñandú"}
    assert registro["acciones"][0]["observacion"] == "observación de la herramienta"
    assert registro["respuesta_final"] == "Respuesta con acentos: á"
    ARCHIVO_TRAZA_PRUEBA.unlink()


def test_registrar_traza_sin_pasos_intermedios_deja_acciones_vacias_y_agrega_lineas():
    registrar_traza("s1", "primera", {"output": "uno"}, ARCHIVO_TRAZA_PRUEBA)
    registrar_traza("s1", "segunda", {"output": "dos"}, ARCHIVO_TRAZA_PRUEBA)

    lineas = ARCHIVO_TRAZA_PRUEBA.read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 2
    assert json.loads(lineas[0])["acciones"] == []
    assert json.loads(lineas[1])["entrada"] == "segunda"
    ARCHIVO_TRAZA_PRUEBA.unlink()


def test_consultar_con_memoria_seguro_registra_la_traza_de_una_consulta_exitosa():
    agente_falso = MagicMock()
    agente_falso.invoke.return_value = {"output": "ok", "intermediate_steps": []}

    with patch("agente_con_memoria.registrar_traza") as traza:
        respuesta, pasos = consultar_con_memoria_seguro(agente_falso, "pregunta", "s1")

    assert respuesta == "ok"
    assert pasos == []
    assert traza.call_count == 1


def test_consultar_con_memoria_seguro_no_registra_traza_si_la_consulta_falla():
    agente_falso = MagicMock()
    agente_falso.invoke.side_effect = ConnectionError("conexión interrumpida")

    with patch("agente_con_memoria.registrar_traza") as traza:
        respuesta, pasos = consultar_con_memoria_seguro(agente_falso, "pregunta", "s1")

    assert respuesta == MENSAJE_ERROR_GENERAL
    assert pasos is None
    assert traza.call_count == 0


def test_consultar_con_memoria_seguro_entrega_la_respuesta_aunque_falle_la_traza():
    agente_falso = MagicMock()
    agente_falso.invoke.return_value = {"output": "ok", "intermediate_steps": []}

    with patch("agente_con_memoria.registrar_traza", side_effect=OSError("disco lleno")):
        respuesta, pasos = consultar_con_memoria_seguro(agente_falso, "pregunta", "s1")

    assert respuesta == "ok"
    assert pasos == []