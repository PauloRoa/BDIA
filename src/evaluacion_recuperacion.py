# evaluacion_recuperacion.py
# Evaluación de la recuperación semántica con un conjunto de preguntas
# etiquetadas a mano. Calcula precisión@k y recall@k por pregunta y sus
# promedios, y guarda el registro de la corrida para compararlo con corridas
# posteriores (otro k, otro chunk_size, otro corpus).
# Flujo: casos -> retriever real -> ids recuperados -> métricas -> archivo .txt

import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from indexar_corpus import (
    CARPETA_VECTORSTORE,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    cargar_vectorstore,
    construir_embeddings,
)
from recuperacion import K_POR_DEFECTO

CARPETA_RESULTADOS = Path(__file__).resolve().parents[1] / "docs"

# Conjunto de evaluación. Cada id relevante se etiquetó leyendo el texto de los
# chunks del corpus, antes de consultar el retriever: etiquetar mirando lo que
# devuelve el retriever mediría el propio sesgo y no la recuperación.
# Un chunk es relevante si, por sí solo, alcanza para responder la pregunta o
# su parte central. Los ids tienen el formato "<fuente>_<n>" que asigna la
# indexación, así que no cambian al reindexar el mismo corpus.
CASOS_EVALUACION = [
    {
        "pregunta": "¿Qué hace ON DELETE CASCADE en una clave foránea?",
        "ids_relevantes": {"clave_foranea.md_1"},
    },
    {
        "pregunta": "¿Por qué el correo de un cliente no es una buena clave primaria?",
        "ids_relevantes": {"clave_primaria.md_1"},
    },
    # Caso difícil: relacion_muchos_a_muchos.md_0 nombra la tabla intermedia,
    # pero solo el _1 dice dónde se guardan los datos propios de la relación.
    {
        "pregunta": "¿Dónde se guarda la cantidad de cada producto en una venta?",
        "ids_relevantes": {"relacion_muchos_a_muchos.md_1"},
    },
    {
        "pregunta": "¿Hay diferencia de rendimiento entre text y varchar(n)?",
        "ids_relevantes": {"tipos_de_dato.md_1"},
    },
    {
        "pregunta": "¿Por qué el total de una venta no se guarda en la tabla venta?",
        "ids_relevantes": {"normalizacion.md_0"},
    },
    {
        "pregunta": "¿Qué restricción impide que un precio sea negativo?",
        "ids_relevantes": {"restricciones.md_0"},
    },
    # Caso difícil: restricciones.md_0 explica cuándo SÍ se usa NOT NULL; la
    # respuesta a cuándo no conviene está solo en el _1.
    {
        "pregunta": "¿Cuándo no conviene agregar NOT NULL a una columna?",
        "ids_relevantes": {"restricciones.md_1"},
    },
    # Dos chunks relevantes: ambos lo afirman por separado.
    {
        "pregunta": "¿Conviene crear un índice sobre una clave foránea?",
        "ids_relevantes": {"clave_foranea.md_1", "indices.md_0"},
    },
    # Dos chunks relevantes: ambos mencionan el índice automático.
    {
        "pregunta": "¿Qué crea PostgreSQL automáticamente al definir una clave primaria?",
        "ids_relevantes": {"clave_primaria.md_0", "indices.md_0"},
    },
    # Caso difícil: indices.md_0 habla del costo de los índices, no de los
    # casos en que no conviene crearlos.
    {
        "pregunta": "¿En qué casos no conviene indexar una columna?",
        "ids_relevantes": {"indices.md_1"},
    },
    # Pregunta que el corpus no puede responder: no tiene ids relevantes.
    {
        "pregunta": "¿Cómo se hace un respaldo de la base de datos?",
        "ids_relevantes": set(),
    },
]


def precision_at_k(ids_recuperados: list[str], ids_relevantes: set[str]) -> float:
    """Fracción de los ids recuperados que son relevantes.
    Devuelve 0.0 si el retriever no devolvió ningún id."""
    # Evita dividir por cero cuando no se recuperó nada.
    if not ids_recuperados:
        return 0.0
    acertados = [i for i in ids_recuperados if i in ids_relevantes]
    return len(acertados) / len(ids_recuperados)


def recall_at_k(ids_recuperados: list[str], ids_relevantes: set[str]) -> float | None:
    """Fracción de los ids relevantes que se recuperaron.
    Devuelve None si el caso no tiene ids relevantes (no hay nada que recuperar)."""
    # None y no 0.0: un caso sin respuesta en el corpus no tiene recall; si
    # valiera 0.0, bajaría el promedio por algo que el retriever no pudo hacer.
    if not ids_relevantes:
        return None
    acertados = [i for i in ids_recuperados if i in ids_relevantes]
    return len(acertados) / len(ids_relevantes)


def promediar(valores) -> float:
    """Promedio que ignora los None y evita dividir por cero."""
    validos = [v for v in valores if v is not None]
    return sum(validos) / len(validos) if validos else 0.0


def verificar_etiquetas(casos: list[dict], ids_indice: set[str]) -> None:
    """Falla si algún id relevante no existe en el índice. Un id mal escrito
    haría que el recall de ese caso fuera 0 sin avisar."""
    desconocidos = sorted(
        {i for caso in casos for i in caso["ids_relevantes"]} - ids_indice
    )
    if desconocidos:
        raise ValueError(
            f"Hay ids relevantes que no existen en el índice: {desconocidos}. "
            "Revisa las etiquetas o ejecuta python src/indexar_corpus.py."
        )


def evaluar_recuperacion(retriever, casos: list[dict], k: int):
    """Consulta el retriever con cada pregunta y calcula precisión y recall
    por caso y sus promedios. Devuelve (resultados, precision_prom, recall_prom)."""
    resultados = []
    for caso in casos:
        # Cada invoke calcula el embedding de la pregunta (consume tokens).
        chunks = retriever.invoke(caso["pregunta"])
        # Se compara por id y no por texto: los ids son estables, el texto no
        # tolera diferencias de espacios o mayúsculas. El corte [:k] garantiza
        # que se evalúan exactamente k, aunque el retriever devuelva más.
        ids_recuperados = [c.id for c in chunks][:k]
        resultados.append(
            {
                "pregunta": caso["pregunta"],
                "ids_relevantes": caso["ids_relevantes"],
                "ids_recuperados": ids_recuperados,
                "precision": precision_at_k(ids_recuperados, caso["ids_relevantes"]),
                "recall": recall_at_k(ids_recuperados, caso["ids_relevantes"]),
            }
        )
    precision_promedio = promediar(r["precision"] for r in resultados)
    recall_promedio = promediar(r["recall"] for r in resultados)
    return resultados, precision_promedio, recall_promedio


def formatear_resultado(resultado: dict) -> str:
    """Línea de una pregunta: precisión, recall (n/a si no aplica) y pregunta."""
    recall_txt = "n/a" if resultado["recall"] is None else f"{resultado['recall']:.2f}"
    return f"{resultado['precision']:.2f}  {recall_txt}  {resultado['pregunta']}"


def formatear_reporte(
    resultados: list[dict],
    precision_promedio: float,
    recall_promedio: float,
    k: int,
    fecha: date,
) -> str:
    """Texto completo del registro: fecha, configuración, una línea por
    pregunta y los promedios."""
    # chunk_size y chunk_overlap se leen de la indexación para que el registro
    # siempre diga con qué configuración se creó el índice evaluado.
    lineas = [
        f"Fecha: {fecha}",
        f"Configuracion: k={k}, chunk_size={CHUNK_SIZE}, chunk_overlap={CHUNK_OVERLAP}",
        "",
    ]
    lineas += [formatear_resultado(r) for r in resultados]
    lineas += [
        "",
        f"promedio -> precision: {precision_promedio:.3f}  recall: {recall_promedio:.3f}",
    ]
    return "\n".join(lineas) + "\n"


def guardar_reporte(ruta: Path, texto: str) -> None:
    """Escribe el registro en un archivo de texto UTF-8."""
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(texto)


if __name__ == "__main__":
    load_dotenv()
    try:
        # Por defecto se evalúa con el mismo k que usa la recuperación. Un
        # argumento permite probar otro valor sin editar el código:
        # python src/evaluacion_recuperacion.py 5
        k = int(sys.argv[1]) if len(sys.argv) > 1 else K_POR_DEFECTO
        if k < 1:
            raise ValueError("k debe ser un entero mayor o igual a 1.")
        vectorstore = cargar_vectorstore(construir_embeddings(), CARPETA_VECTORSTORE)
        verificar_etiquetas(CASOS_EVALUACION, set(vectorstore.get()["ids"]))
        # El mismo k va al retriever y a la evaluación.
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        resultados, precision_promedio, recall_promedio = evaluar_recuperacion(
            retriever, CASOS_EVALUACION, k
        )
    except Exception as error:
        # Cualquier falla (clave, cuota, red, etiquetas) se informa sin
        # traceback largo.
        print("No se pudo evaluar la recuperación:", type(error).__name__)
        print("Detalle técnico:", error)
        raise SystemExit(1)

    # En consola se muestran además los ids, que sirven para depurar un caso
    # con recall bajo; el archivo guarda solo las métricas.
    for r in resultados:
        print(formatear_resultado(r))
        print("   relevantes:", sorted(r["ids_relevantes"]))
        print("   recuperados:", r["ids_recuperados"])
    fecha = date.today()
    texto = formatear_reporte(
        resultados, precision_promedio, recall_promedio, k, fecha
    )
    print()
    print(texto.splitlines()[-1])
    # Un archivo por fecha y por k: corridas con otra configuración no
    # sobrescriben a las anteriores y se pueden comparar.
    ruta = CARPETA_RESULTADOS / f"resultados_evaluacion_{fecha}_k{k}.txt"
    guardar_reporte(ruta, texto)
    print(f"Resultados guardados en {ruta}")