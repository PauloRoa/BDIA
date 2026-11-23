import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from consumir_gemini import MODELO
from evaluacion_recuperacion import CASOS_EVALUACION
from recuperacion import PROMPT_TEMPLATE
from registro_rag import (
    PREGUNTAS_DE_REGISTRO,
    RUTA_REGISTROS,
    calcular_costo_tokens,
    construir_modelo,
    guardar_registro,
    medir,
    registrar_consulta,
)

PREGUNTA = "¿Qué hace ON DELETE CASCADE en una clave foránea?"
VECTOR = [0.1, 0.2]
USO = {
    "input_tokens": 144,
    "output_tokens": 404,
    "total_tokens": 548,
    "input_token_details": {"cache_read": 0},
    "output_token_details": {"reasoning": 383},
}


def embeddings_falsos():
    embeddings = MagicMock()
    embeddings.embed_query.return_value = VECTOR
    return embeddings


def vectorstore_falso(chunks=None):
    if chunks is None:
        chunks = [
            Document(page_content="texto uno", metadata={"fuente": "a.md"}),
            Document(page_content="texto dos", metadata={"fuente": "b.md"}),
        ]
    vectorstore = MagicMock()
    vectorstore.similarity_search_by_vector.return_value = chunks
    return vectorstore


def modelo_falso(respuesta, prompts):
    # Guarda cada prompt recibido para poder revisarlo después.
    def invoke(prompt):
        prompts.append(prompt)
        return respuesta

    modelo = MagicMock()
    modelo.invoke.side_effect = invoke
    return modelo


def respuesta_con_uso():
    return AIMessage(content="Respuesta [1]", usage_metadata=USO)


# --- medir ---


def test_medir_guarda_la_duracion_de_la_etapa():
    tiempos = {}
    with patch("registro_rag.time.perf_counter", side_effect=[10.0, 12.5]):
        with medir(tiempos, "etapa"):
            pass
    assert tiempos == {"etapa": 2.5}


def test_medir_no_guarda_la_etapa_si_el_bloque_falla():
    tiempos = {}
    with pytest.raises(RuntimeError):
        with medir(tiempos, "etapa"):
            raise RuntimeError("falla")
    assert tiempos == {}


# --- calcular_costo_tokens ---


def test_calcular_costo_tokens_usa_precio_de_entrada_y_de_salida():
    # 144 * 0.25 / 1e6 + 404 * 1.50 / 1e6 = 0.000036 + 0.000606
    assert calcular_costo_tokens(144, 404) == pytest.approx(0.000642)


def test_calcular_costo_tokens_sin_tokens_es_cero():
    assert calcular_costo_tokens(0, 0) == 0


# --- construir_modelo ---


def test_construir_modelo_usa_modelo_clave_temperatura_y_timeout_del_proyecto():
    with patch("registro_rag.ChatGoogleGenerativeAI") as clase_modelo:
        with patch("registro_rag.os.getenv", return_value="clave-de-prueba"):
            construir_modelo()
    clase_modelo.assert_called_once_with(
        model=MODELO,
        google_api_key="clave-de-prueba",
        temperature=0,
        timeout=60,
    )


# --- registrar_consulta ---


def test_registrar_consulta_devuelve_las_claves_esperadas_en_orden():
    registro = registrar_consulta(
        PREGUNTA, embeddings_falsos(), vectorstore_falso(), modelo_falso(respuesta_con_uso(), []), 3
    )
    assert list(registro) == [
        "timestamp",
        "pregunta",
        "k",
        "tiempos_ms",
        "tiempo_total_ms",
        "tokens",
        "costo_usd",
    ]
    assert registro["pregunta"] == PREGUNTA
    assert registro["k"] == 3


def test_registrar_consulta_mide_las_tres_etapas_y_el_total_las_suma():
    # Un reloj simulado: cada etapa lee el reloj dos veces (inicio y fin).
    # embed_query dura 0.1 s, busqueda_vectorial 0.2 s y generacion 2.0 s.
    with patch("registro_rag.time.perf_counter", side_effect=[0.0, 0.1, 1.0, 1.2, 5.0, 7.0]):
        registro = registrar_consulta(
            PREGUNTA, embeddings_falsos(), vectorstore_falso(), modelo_falso(respuesta_con_uso(), []), 3
        )
    assert list(registro["tiempos_ms"]) == ["embed_query", "busqueda_vectorial", "generacion"]
    assert registro["tiempos_ms"]["embed_query"] == pytest.approx(100.0)
    assert registro["tiempos_ms"]["busqueda_vectorial"] == pytest.approx(200.0)
    assert registro["tiempos_ms"]["generacion"] == pytest.approx(2000.0)
    assert registro["tiempo_total_ms"] == pytest.approx(2300.0)


def test_registrar_consulta_guarda_los_tokens_reales_y_calcula_el_costo():
    registro = registrar_consulta(
        PREGUNTA, embeddings_falsos(), vectorstore_falso(), modelo_falso(respuesta_con_uso(), []), 3
    )
    assert registro["tokens"] == USO
    assert registro["costo_usd"] == pytest.approx(0.000642)


def test_registrar_consulta_sin_usage_metadata_deja_tokens_y_costo_en_none():
    respuesta = AIMessage(content="Respuesta sin datos de uso")
    registro = registrar_consulta(
        PREGUNTA, embeddings_falsos(), vectorstore_falso(), modelo_falso(respuesta, []), 3
    )
    assert registro["tokens"] is None
    assert registro["costo_usd"] is None


def test_registrar_consulta_calcula_el_embedding_una_vez_y_busca_por_vector():
    embeddings = embeddings_falsos()
    vectorstore = vectorstore_falso()
    registrar_consulta(PREGUNTA, embeddings, vectorstore, modelo_falso(respuesta_con_uso(), []), 3)
    embeddings.embed_query.assert_called_once_with(PREGUNTA)
    vectorstore.similarity_search_by_vector.assert_called_once_with(VECTOR, k=3)
    # La búsqueda por texto volvería a calcular el embedding.
    vectorstore.similarity_search.assert_not_called()


def test_registrar_consulta_usa_el_k_indicado():
    vectorstore = vectorstore_falso()
    registro = registrar_consulta(
        PREGUNTA, embeddings_falsos(), vectorstore, modelo_falso(respuesta_con_uso(), []), 6
    )
    vectorstore.similarity_search_by_vector.assert_called_once_with(VECTOR, k=6)
    assert registro["k"] == 6


def test_registrar_consulta_envia_al_modelo_el_prompt_con_contexto_numerado_y_la_pregunta():
    prompts = []
    registrar_consulta(
        PREGUNTA, embeddings_falsos(), vectorstore_falso(), modelo_falso(respuesta_con_uso(), prompts), 3
    )
    esperado = PROMPT_TEMPLATE.format(
        contexto="[1] texto uno\n\n[2] texto dos",
        pregunta=PREGUNTA,
    )
    assert prompts == [esperado]


def test_registrar_consulta_marca_la_hora_en_utc():
    registro = registrar_consulta(
        PREGUNTA, embeddings_falsos(), vectorstore_falso(), modelo_falso(respuesta_con_uso(), []), 3
    )
    assert datetime.fromisoformat(registro["timestamp"]).utcoffset() == timedelta(0)


def test_registrar_consulta_rechaza_preguntas_no_validas_sin_llamar_a_la_api():
    for pregunta in ["", "   ", None, 5]:
        embeddings = embeddings_falsos()
        modelo = modelo_falso(respuesta_con_uso(), [])
        with pytest.raises(ValueError, match="no puede estar vacía"):
            registrar_consulta(pregunta, embeddings, vectorstore_falso(), modelo, 3)
        embeddings.embed_query.assert_not_called()
        modelo.invoke.assert_not_called()


def test_registrar_consulta_rechaza_k_menor_a_uno_sin_llamar_a_la_api():
    embeddings = embeddings_falsos()
    with pytest.raises(ValueError, match="k debe ser al menos 1"):
        registrar_consulta(PREGUNTA, embeddings, vectorstore_falso(), modelo_falso(respuesta_con_uso(), []), 0)
    embeddings.embed_query.assert_not_called()


def test_registrar_consulta_con_indice_vacio_falla_sin_llamar_al_modelo():
    modelo = modelo_falso(respuesta_con_uso(), [])
    with pytest.raises(ValueError, match="indexar_corpus"):
        registrar_consulta(PREGUNTA, embeddings_falsos(), vectorstore_falso(chunks=[]), modelo, 3)
    modelo.invoke.assert_not_called()


def test_registrar_consulta_propaga_la_falla_del_modelo_y_no_devuelve_registro():
    modelo = MagicMock()
    modelo.invoke.side_effect = TimeoutError("sin respuesta")
    with pytest.raises(TimeoutError):
        registrar_consulta(PREGUNTA, embeddings_falsos(), vectorstore_falso(), modelo, 3)


# --- guardar_registro ---


def test_guardar_registro_agrega_una_linea_json_por_registro():
    ruta = Path(__file__).parent / "registros_temporales.jsonl"
    primero = {"pregunta": "¿Qué hace ON DELETE CASCADE?", "k": 3, "tokens": None}
    segundo = {"pregunta": "otra pregunta", "k": 6, "tokens": USO}
    try:
        guardar_registro(primero, ruta)
        guardar_registro(segundo, ruta)
        texto = ruta.read_text(encoding="utf-8")
        lineas = texto.splitlines()
        assert len(lineas) == 2
        assert json.loads(lineas[0]) == primero
        assert json.loads(lineas[1]) == segundo
        # Las tildes y los signos del español se guardan legibles, no escapados.
        assert "¿Qué" in lineas[0]
    finally:
        if ruta.exists():
            ruta.unlink()


# --- constantes ---


def test_el_registro_se_guarda_en_docs_con_el_nombre_esperado():
    assert RUTA_REGISTROS.name == "registros_latencia_costo.jsonl"
    assert RUTA_REGISTROS.parent.name == "docs"


def test_las_preguntas_de_registro_son_del_conjunto_de_evaluacion_y_de_distinto_largo():
    preguntas_evaluacion = [caso["pregunta"] for caso in CASOS_EVALUACION]
    assert len(PREGUNTAS_DE_REGISTRO) == 3
    for pregunta in PREGUNTAS_DE_REGISTRO:
        assert pregunta in preguntas_evaluacion
    assert len({len(pregunta) for pregunta in PREGUNTAS_DE_REGISTRO}) == 3