from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from indexar_corpus import (
    CHUNK_SIZE,
    MODELO_EMBEDDINGS,
    cargar_corpus,
    cargar_vectorstore,
    construir_embeddings,
    dividir_documentos,
    generar_ids,
    indexar_corpus,
)


class AlmacenFalso:
    def __init__(self, ids_guardados):
        self.ids_guardados = ids_guardados
        self.borrados = []
        self.coleccion_borrada = False

    def get(self):
        return {"ids": self.ids_guardados}

    def delete(self, ids):
        self.borrados.extend(ids)

    def delete_collection(self):
        self.coleccion_borrada = True


def chunks_de(fuente, cantidad):
    return [
        Document(page_content=f"chunk {numero}", metadata={"fuente": fuente})
        for numero in range(cantidad)
    ]


def chroma_falso(almacen):
    recibido = {}

    def from_documents(**kwargs):
        recibido.update(kwargs)
        return almacen

    chroma = MagicMock()
    chroma.from_documents.side_effect = from_documents
    return chroma, recibido


def test_cargar_corpus_lee_al_menos_cinco_documentos_con_su_fuente():
    documentos = cargar_corpus()
    fuentes = [documento.metadata["fuente"] for documento in documentos]

    assert len(documentos) >= 5
    assert all(fuente.endswith(".md") for fuente in fuentes)
    assert all(Path(fuente).name == fuente for fuente in fuentes)
    assert len(set(fuentes)) == len(fuentes)
    assert all(documento.page_content.strip() for documento in documentos)


def test_cargar_corpus_falla_si_no_hay_documentos_md():
    with pytest.raises(ValueError):
        cargar_corpus(Path(__file__).parent / "carpeta_inexistente")


def test_dividir_documentos_parte_el_texto_y_conserva_la_fuente():
    documento = Document(
        page_content="Primer párrafo.\n\nSegundo párrafo.",
        metadata={"fuente": "ejemplo.md"},
    )

    chunks = dividir_documentos([documento], chunk_size=20, chunk_overlap=5)

    assert [chunk.page_content for chunk in chunks] == [
        "Primer párrafo.",
        "Segundo párrafo.",
    ]
    assert all(chunk.metadata == {"fuente": "ejemplo.md"} for chunk in chunks)


def test_dividir_el_corpus_real_genera_mas_chunks_que_documentos():
    documentos = cargar_corpus()

    chunks = dividir_documentos(documentos)

    assert len(chunks) > len(documentos)
    assert all(len(chunk.page_content) <= CHUNK_SIZE for chunk in chunks)


def test_generar_ids_numera_los_chunks_por_documento():
    chunks = chunks_de("a.md", 2) + chunks_de("b.md", 1)

    assert generar_ids(chunks) == ["a.md_0", "a.md_1", "b.md_0"]
    assert generar_ids([]) == []


def test_indexar_corpus_guarda_los_chunks_con_ids_estables():
    chunks = chunks_de("a.md", 2)
    almacen = AlmacenFalso(["a.md_0", "a.md_1"])
    chroma, recibido = chroma_falso(almacen)

    with patch("indexar_corpus.Chroma", chroma):
        indexar_corpus(chunks, "embeddings", Path("carpeta_prueba"))

    assert recibido["ids"] == ["a.md_0", "a.md_1"]
    assert recibido["documents"] == chunks
    assert recibido["embedding"] == "embeddings"
    assert recibido["persist_directory"] == str(Path("carpeta_prueba"))


def test_indexar_corpus_borra_los_ids_que_ya_no_corresponden_a_ningun_chunk():
    almacen = AlmacenFalso(["a.md_0", "a.md_1", "a.md_2", "b.md_0"])
    chroma, _ = chroma_falso(almacen)

    with patch("indexar_corpus.Chroma", chroma):
        indexar_corpus(chunks_de("a.md", 2), "embeddings")

    assert almacen.borrados == ["a.md_2", "b.md_0"]


def test_indexar_corpus_no_borra_nada_si_el_indice_ya_coincide():
    almacen = AlmacenFalso(["a.md_0", "a.md_1"])
    chroma, _ = chroma_falso(almacen)

    with patch("indexar_corpus.Chroma", chroma):
        indexar_corpus(chunks_de("a.md", 2), "embeddings")

    assert almacen.borrados == []


def test_indexar_corpus_propaga_el_fallo_de_la_api_sin_tocar_el_indice_anterior():
    almacen = AlmacenFalso(["a.md_0", "viejo.md_0"])
    chroma = MagicMock(return_value=almacen)
    chroma.from_documents.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED")

    with patch("indexar_corpus.Chroma", chroma):
        with pytest.raises(RuntimeError):
            indexar_corpus(chunks_de("a.md", 1), "embeddings")

    assert almacen.borrados == []
    assert almacen.coleccion_borrada is False


def test_cargar_vectorstore_se_reconecta_sin_recalcular_embeddings():
    chroma = MagicMock()

    with patch("indexar_corpus.Chroma", chroma):
        cargar_vectorstore("embeddings", Path("carpeta_prueba"))

    assert chroma.from_documents.call_count == 0
    assert chroma.call_count == 1


def test_construir_embeddings_pasa_la_clave_y_el_modelo():
    recibido = {}

    def embeddings_falsos(**kwargs):
        recibido.update(kwargs)

    with patch("indexar_corpus.os.getenv", return_value="clave_de_prueba"), \
            patch("indexar_corpus.GoogleGenerativeAIEmbeddings", embeddings_falsos):
        construir_embeddings()

    assert recibido == {"model": MODELO_EMBEDDINGS, "google_api_key": "clave_de_prueba"}


def test_construir_embeddings_falla_si_falta_la_clave():
    with patch("indexar_corpus.os.getenv", return_value=None):
        with pytest.raises(ValueError):
            construir_embeddings()