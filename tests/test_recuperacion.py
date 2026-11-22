from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from recuperacion import (
    FUENTE_INVALIDA,
    K_POR_DEFECTO,
    construir_prompt,
    formatear_contexto,
    resolver_citas,
)


def chunks_de_prueba():
    return [
        Document(page_content="Primer chunk.", metadata={"fuente": "a.md"}),
        Document(page_content="Segundo chunk.", metadata={"fuente": "b.md"}),
        Document(page_content="Tercer chunk.", metadata={"fuente": "a.md"}),
    ]


def chroma_falso(chunks):
    """Reemplaza la clase Chroma de indexar_corpus: al recuperar devuelve los
    chunks dados y permite ver con qué se creó y qué k se pidió."""
    chroma = MagicMock()
    chroma.return_value.as_retriever.return_value.invoke.return_value = chunks
    return chroma


def prompt_con_chroma_falso(pregunta, chunks, **argumentos):
    chroma = chroma_falso(chunks)
    with patch("indexar_corpus.Chroma", chroma), patch(
        "recuperacion.construir_embeddings", return_value="embeddings"
    ):
        resultado = construir_prompt(pregunta, **argumentos)
    return resultado, chroma


def test_formatear_contexto_numera_desde_uno_y_mapea_fuentes():
    contexto, citas = formatear_contexto(chunks_de_prueba())

    assert contexto == "[1] Primer chunk.\n\n[2] Segundo chunk.\n\n[3] Tercer chunk."
    assert citas == {1: "a.md", 2: "b.md", 3: "a.md"}


def test_formatear_contexto_sin_fuente_usa_desconocida():
    chunk = Document(page_content="Sin metadata.", metadata={})

    _, citas = formatear_contexto([chunk])

    assert citas == {1: "desconocida"}


def test_formatear_contexto_sin_chunks():
    assert formatear_contexto([]) == ("", {})


def test_construir_prompt_devuelve_k_citas_y_k_bloques():
    (prompt, citas), _ = prompt_con_chroma_falso("¿Qué es una clave?", chunks_de_prueba())

    assert list(citas) == [1, 2, 3]
    assert "desconocida" not in citas.values()
    for numero in (1, 2, 3):
        assert f"[{numero}] " in prompt
    assert "[4] " not in prompt


def test_construir_prompt_conserva_la_pregunta_exacta():
    pregunta = " ¿Qué es {id} en una tabla? "

    (prompt, _), _ = prompt_con_chroma_falso(pregunta, chunks_de_prueba())

    assert f"Pregunta: {pregunta}\n\nRespuesta:" in prompt


def test_construir_prompt_incluye_las_instrucciones_de_citar():
    (prompt, _), _ = prompt_con_chroma_falso("¿Pregunta?", chunks_de_prueba())

    assert "SOLO el contexto" in prompt
    assert "su número entre corchetes" in prompt
    assert "dilo explícitamente en vez de inventar" in prompt
    assert "Contexto:\n[1] Primer chunk." in prompt


def test_construir_prompt_pide_k_por_defecto_y_k_indicado():
    _, chroma = prompt_con_chroma_falso("¿Pregunta?", chunks_de_prueba())
    chroma.return_value.as_retriever.assert_called_once_with(
        search_kwargs={"k": K_POR_DEFECTO}
    )

    _, chroma = prompt_con_chroma_falso("¿Pregunta?", chunks_de_prueba(), k=5)
    chroma.return_value.as_retriever.assert_called_once_with(search_kwargs={"k": 5})


def test_construir_prompt_se_reconecta_al_indice_sin_reindexar():
    _, chroma = prompt_con_chroma_falso(
        "¿Pregunta?", chunks_de_prueba(), persist_directory="mi_indice"
    )

    chroma.assert_called_once_with(
        persist_directory="mi_indice", embedding_function="embeddings"
    )
    assert chroma.from_documents.call_count == 0


def test_construir_prompt_rechaza_preguntas_vacias_sin_tocar_el_indice():
    for pregunta in ["", "   ", None, 5]:
        with patch("recuperacion.construir_embeddings") as embeddings, patch(
            "recuperacion.cargar_vectorstore"
        ) as reconexion:
            with pytest.raises(ValueError, match="no puede estar vacía"):
                construir_prompt(pregunta)
        assert embeddings.call_count == 0
        assert reconexion.call_count == 0


def test_resolver_citas_traduce_numeros_a_fuentes_sin_repetir():
    citas = {1: "a.md", 2: "b.md", 3: "c.md"}

    resultado = resolver_citas("Dato [3] y dato [1], otra vez [1].", citas)

    assert resultado == {1: "a.md", 3: "c.md"}


def test_resolver_citas_marca_un_numero_inexistente_como_invalido():
    resultado = resolver_citas("Dato inventado [99].", {1: "a.md"})

    assert resultado == {99: FUENTE_INVALIDA}


def test_resolver_citas_sin_citas_devuelve_vacio():
    assert resolver_citas("Respuesta sin citas.", {1: "a.md"}) == {}