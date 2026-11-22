import re
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

from evaluacion_recuperacion import (
    CASOS_EVALUACION,
    evaluar_recuperacion,
    formatear_reporte,
    formatear_resultado,
    guardar_reporte,
    precision_at_k,
    promediar,
    recall_at_k,
    verificar_etiquetas,
)
from indexar_corpus import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    cargar_corpus,
    dividir_documentos,
    generar_ids,
)


def retriever_falso(ids_por_pregunta):
    """Retriever simulado: devuelve Documents con los ids indicados para cada
    pregunta, sin consultar Chroma ni calcular embeddings."""
    retriever = MagicMock()
    retriever.invoke.side_effect = lambda pregunta: [
        Document(page_content="texto", id=i) for i in ids_por_pregunta[pregunta]
    ]
    return retriever


# --- precision_at_k ---


def test_precision_es_la_fraccion_de_recuperados_relevantes():
    assert precision_at_k(["a", "b", "c"], {"a"}) == 1 / 3
    assert precision_at_k(["a", "b", "c"], {"a", "c"}) == 2 / 3


def test_precision_vale_uno_si_todos_son_relevantes_y_cero_si_ninguno():
    assert precision_at_k(["a", "b"], {"a", "b", "c"}) == 1.0
    assert precision_at_k(["x", "y"], {"a"}) == 0.0


def test_precision_con_lista_vacia_vale_cero_sin_dividir_por_cero():
    assert precision_at_k([], {"a"}) == 0.0


def test_precision_sin_ids_relevantes_vale_cero():
    assert precision_at_k(["a", "b"], set()) == 0.0


# --- recall_at_k ---


def test_recall_es_la_fraccion_de_relevantes_recuperados():
    assert recall_at_k(["a", "x"], {"a", "b"}) == 0.5
    assert recall_at_k(["a", "b", "x"], {"a", "b"}) == 1.0
    assert recall_at_k(["x", "y"], {"a", "b"}) == 0.0


def test_recall_sin_ids_relevantes_es_none_y_no_cero():
    assert recall_at_k(["a", "b"], set()) is None
    assert recall_at_k([], set()) is None


def test_recall_con_lista_vacia_y_relevantes_vale_cero():
    assert recall_at_k([], {"a"}) == 0.0


# --- promediar ---


def test_promediar_ignora_los_none():
    assert promediar([1.0, None, 0.5]) == 0.75


def test_promediar_sin_valores_o_solo_none_devuelve_cero():
    assert promediar([]) == 0.0
    assert promediar([None, None]) == 0.0


# --- verificar_etiquetas ---


def test_verificar_etiquetas_acepta_ids_que_existen_y_casos_sin_relevantes():
    casos = [
        {"ids_relevantes": {"a_0", "b_1"}},
        {"ids_relevantes": set()},
    ]
    assert verificar_etiquetas(casos, {"a_0", "b_1", "c_0"}) is None


def test_verificar_etiquetas_falla_e_informa_el_id_desconocido():
    casos = [{"ids_relevantes": {"a_0", "indices.md_9"}}]
    with pytest.raises(ValueError, match="indices.md_9"):
        verificar_etiquetas(casos, {"a_0"})


# --- evaluar_recuperacion ---


def test_evaluar_calcula_metricas_por_caso_y_promedios():
    casos = [
        {"pregunta": "pregunta A", "ids_relevantes": {"a"}},
        {"pregunta": "pregunta B", "ids_relevantes": set()},
    ]
    retriever = retriever_falso(
        {"pregunta A": ["a", "b", "c"], "pregunta B": ["x", "y", "z"]}
    )
    resultados, precision_prom, recall_prom = evaluar_recuperacion(
        retriever, casos, k=3
    )
    assert resultados[0]["ids_recuperados"] == ["a", "b", "c"]
    assert resultados[0]["precision"] == 1 / 3
    assert resultados[0]["recall"] == 1.0
    assert resultados[1]["precision"] == 0.0
    assert resultados[1]["recall"] is None
    # La pregunta sin respuesta baja la precisión promedio pero no el recall.
    assert precision_prom == (1 / 3 + 0.0) / 2
    assert recall_prom == 1.0


def test_evaluar_consulta_el_retriever_con_cada_pregunta_exacta():
    casos = [
        {"pregunta": "pregunta A", "ids_relevantes": {"a"}},
        {"pregunta": "pregunta B", "ids_relevantes": {"b"}},
    ]
    retriever = retriever_falso({"pregunta A": ["a"], "pregunta B": ["b"]})
    evaluar_recuperacion(retriever, casos, k=1)
    assert retriever.invoke.call_count == 2
    retriever.invoke.assert_any_call("pregunta A")
    retriever.invoke.assert_any_call("pregunta B")


def test_evaluar_corta_a_k_aunque_el_retriever_devuelva_mas():
    casos = [{"pregunta": "pregunta A", "ids_relevantes": {"e"}}]
    retriever = retriever_falso({"pregunta A": ["a", "b", "c", "d", "e"]})
    resultados, _, recall_prom = evaluar_recuperacion(retriever, casos, k=3)
    assert resultados[0]["ids_recuperados"] == ["a", "b", "c"]
    # El relevante quedó en la posición 5, fuera de k=3.
    assert recall_prom == 0.0


def test_evaluar_con_retriever_sin_resultados_da_precision_y_recall_cero():
    casos = [{"pregunta": "pregunta A", "ids_relevantes": {"a"}}]
    retriever = retriever_falso({"pregunta A": []})
    resultados, precision_prom, recall_prom = evaluar_recuperacion(
        retriever, casos, k=3
    )
    assert resultados[0]["ids_recuperados"] == []
    assert precision_prom == 0.0
    assert recall_prom == 0.0


# --- formato del registro ---


def test_formatear_resultado_con_recall():
    resultado = {"pregunta": "¿Qué es un id?", "precision": 1 / 3, "recall": 1.0}
    assert formatear_resultado(resultado) == "0.33  1.00  ¿Qué es un id?"


def test_formatear_resultado_sin_recall_muestra_na():
    resultado = {"pregunta": "¿Qué es un id?", "precision": 0.0, "recall": None}
    assert formatear_resultado(resultado) == "0.00  n/a  ¿Qué es un id?"


def test_formatear_reporte_tiene_fecha_configuracion_lineas_y_promedios():
    resultados = [
        {"pregunta": "pregunta A", "precision": 1 / 3, "recall": 1.0},
        {"pregunta": "pregunta B", "precision": 0.0, "recall": None},
    ]
    texto = formatear_reporte(resultados, 0.25, 0.75, k=3, fecha=date(2026, 11, 22))
    esperado = (
        "Fecha: 2026-11-22\n"
        f"Configuracion: k=3, chunk_size={CHUNK_SIZE}, chunk_overlap={CHUNK_OVERLAP}\n"
        "\n"
        "0.33  1.00  pregunta A\n"
        "0.00  n/a  pregunta B\n"
        "\n"
        "promedio -> precision: 0.250  recall: 0.750\n"
    )
    assert texto == esperado


def test_formatear_reporte_registra_el_k_recibido():
    texto = formatear_reporte([], 0.0, 0.0, k=5, fecha=date(2026, 11, 22))
    assert "Configuracion: k=5," in texto


def test_guardar_reporte_escribe_el_texto_en_utf8():
    ruta = Path(__file__).parent / "reporte_temporal.txt"
    texto = "¿Cómo se hace un respaldo?\n"
    try:
        guardar_reporte(ruta, texto)
        assert ruta.read_text(encoding="utf-8") == texto
    finally:
        # El archivo es temporal: no debe quedar en el repositorio.
        if ruta.exists():
            ruta.unlink()


# --- conjunto de casos de evaluación ---


def test_los_casos_tienen_pregunta_y_ids_relevantes_como_conjunto():
    for caso in CASOS_EVALUACION:
        assert isinstance(caso["pregunta"], str) and caso["pregunta"].strip()
        # Un texto suelto en lugar de un set haría que "in" compare subcadenas.
        assert isinstance(caso["ids_relevantes"], set)


def test_las_preguntas_no_se_repiten():
    preguntas = [caso["pregunta"] for caso in CASOS_EVALUACION]
    assert len(preguntas) == len(set(preguntas))


def test_el_conjunto_incluye_casos_sin_respuesta_y_con_varios_relevantes():
    cantidades = [len(caso["ids_relevantes"]) for caso in CASOS_EVALUACION]
    assert 0 in cantidades
    assert max(cantidades) > 1


def test_los_ids_relevantes_tienen_el_formato_fuente_numero():
    for caso in CASOS_EVALUACION:
        for chunk_id in caso["ids_relevantes"]:
            assert re.fullmatch(r"[a-z_]+\.md_\d+", chunk_id)


def test_todos_los_ids_relevantes_existen_en_el_corpus_actual():
    # Se generan los ids con la misma indexación, sin llamar a la API.
    ids_corpus = set(generar_ids(dividir_documentos(cargar_corpus())))
    assert verificar_etiquetas(CASOS_EVALUACION, ids_corpus) is None