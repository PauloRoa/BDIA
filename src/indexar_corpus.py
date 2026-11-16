import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from enrutamiento import es_error_de_configuracion

CARPETA_CORPUS = Path(__file__).resolve().parents[1] / "corpus"
CARPETA_VECTORSTORE = Path(__file__).resolve().parents[1] / "vectorstore"
MODELO_EMBEDDINGS = "models/gemini-embedding-001"

# Los documentos tienen párrafos, así que el splitter recursivo corta primero
# entre párrafos. Con 500 caracteres cada documento queda en dos chunks, y el
# traslape es el 15 % del tamaño.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 75


def cargar_corpus(carpeta: Path = CARPETA_CORPUS) -> list[Document]:
    """Lee cada archivo .md de la carpeta como un documento cuya fuente es el
    nombre del archivo."""
    documentos = [
        Document(
            page_content=ruta.read_text(encoding="utf-8"),
            metadata={"fuente": ruta.name},
        )
        for ruta in sorted(carpeta.glob("*.md"))
    ]
    if not documentos:
        raise ValueError(f"No hay documentos .md en {carpeta}.")
    return documentos


def dividir_documentos(
    documentos: list[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Document]:
    """Parte cada documento en chunks. Cada chunk conserva la fuente de su
    documento."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(documentos)


def construir_embeddings() -> GoogleGenerativeAIEmbeddings:
    clave = os.getenv("API_KEY")
    if not clave:
        raise ValueError('Falta API_KEY. Defínela en tu archivo ".env".')
    return GoogleGenerativeAIEmbeddings(
        model=MODELO_EMBEDDINGS, google_api_key=clave
    )


def generar_ids(chunks: list[Document]) -> list[str]:
    """Un id estable por chunk: la fuente y su número dentro del documento,
    por ejemplo clave_foranea.md_0."""
    contadores = {}
    ids = []
    for chunk in chunks:
        fuente = chunk.metadata["fuente"]
        numero = contadores.get(fuente, 0)
        ids.append(f"{fuente}_{numero}")
        contadores[fuente] = numero + 1
    return ids


def indexar_corpus(
    chunks: list[Document], embeddings, carpeta: Path = CARPETA_VECTORSTORE
) -> Chroma:
    """Deja el índice igual al corpus. Guardar con ids estables actualiza los
    chunks que ya existían en vez de duplicarlos, y se borran los ids que ya no
    corresponden a ningún chunk."""
    ids = generar_ids(chunks)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(carpeta),
        ids=ids,
    )
    sobrantes = [
        id_guardado for id_guardado in vectorstore.get()["ids"] if id_guardado not in ids
    ]
    if sobrantes:
        vectorstore.delete(ids=sobrantes)
    return vectorstore


def cargar_vectorstore(embeddings, carpeta: Path = CARPETA_VECTORSTORE) -> Chroma:
    """Se reconecta al índice guardado en disco sin calcular ningún embedding."""
    return Chroma(persist_directory=str(carpeta), embedding_function=embeddings)


if __name__ == "__main__":
    load_dotenv()
    try:
        documentos = cargar_corpus()
        chunks = dividir_documentos(documentos)
        embeddings = construir_embeddings()
    except ValueError as error:
        print(error)
        raise SystemExit(1)

    try:
        indexar_corpus(chunks, embeddings)
    except Exception as error:
        mensaje = str(error)
        if "429" in mensaje or "RESOURCE_EXHAUSTED" in mensaje:
            print("Límite de peticiones alcanzado. Espera un minuto y vuelve a ejecutar.")
        elif es_error_de_configuracion(error):
            print('La API rechazó tu clave. Revisa el valor de API_KEY en tu ".env".')
        else:
            print("No se pudo indexar el corpus:", type(error).__name__)
            print("Detalle técnico:", mensaje)
        print("El índice no se actualizó: vuelve a ejecutar el script.")
        raise SystemExit(1)

    print(
        f"Indexados {len(chunks)} chunks de {len(documentos)} documentos "
        f"en {CARPETA_VECTORSTORE.name}/"
    )
    recargado = cargar_vectorstore(embeddings)
    print(f"Chunks al reconectar con el índice: {recargado._collection.count()}")