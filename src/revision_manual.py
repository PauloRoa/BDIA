import json
import os

RUTA_REVISION = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "revision_manual.json"))

revision_manual = [
    {
        "caso": 18,
        "consulta": "¿Qué hace la opción ON DELETE CASCADE en una clave foránea?",
        "f1": 0.261,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": "Dice lo mismo con otros términos: “registro” por “fila”, y “registros relacionados en la tabla hija” por “las filas que referencian a una fila”. La paráfrasis explica el F1 bajo.",
    },
    {
        "caso": 14,
        "consulta": "¿Qué exige la tercera forma normal?",
        "f1": 0.388,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": "Cubre las dos condiciones de la referencia. Agrega el término “dependencias transitivas” y una explicación, lo que baja la precisión.",
    },
    {
        "caso": 11,
        "consulta": "¿Qué es un índice en una base de datos relacional?",
        "f1": 0.452,
        "correccion_factual": "si",
        "completitud": "parcial",
        "contradiccion": "no",
        "nota": "Explica que acelera la búsqueda, pero omite el costo que menciona la referencia: espacio adicional y escrituras más lentas.",
    },
    {
        "caso": 19,
        "consulta": "¿Qué es una restricción CHECK en PostgreSQL?",
        "f1": 0.458,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": "“Para que sean aceptados” equivale a “antes de guardarlos”. Que hable de “una o más columnas” amplía la referencia, pero es correcto y no la contradice.",
    },
    {
        "caso": 2,
        "consulta": "¿Qué es una clave foránea en una base de datos relacional?",
        "f1": 0.471,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": "“Vínculo lógico con la clave primaria de otra tabla” equivale a “referencia”. Agrega contenido correcto: clave compuesta e integridad referencial.",
    },
    {
        "caso": 4,
        "consulta": "¿Cuántos bytes ocupa el tipo INTEGER en PostgreSQL?",
        "f1": 0.762,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": "Mismo dato: 4 bytes. Solo agrega palabras (“exactamente”, “de almacenamiento”).",
    },
    {
        "caso": 5,
        "consulta": "¿Cuántos bytes ocupa el tipo BIGINT en PostgreSQL?",
        "f1": 0.762,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": "Mismo dato: 8 bytes. Mismo patrón que el caso 4.",
    },
    {
        "caso": 6,
        "consulta": "¿Quién propuso el modelo relacional y en qué año?",
        "f1": 0.8,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": "Mismo nombre y año; solo cambia a voz pasiva.",
    },
    {
        "caso": 15,
        "consulta": "¿Cómo se representa una relación de muchos a muchos en un modelo relacional?",
        "f1": 0.837,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": "“Llaves foráneas” es sinónimo de “claves foráneas”. Agrega “asociativa”, que es correcto.",
    },
    {
        "caso": 7,
        "consulta": "¿Cuál es la longitud máxima de un identificador en PostgreSQL?",
        "f1": 1.0,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": "Respuesta idéntica a la referencia.",
    },
]


if __name__ == "__main__":
    with open(RUTA_REVISION, "w", encoding="utf-8") as archivo:
        json.dump(revision_manual, archivo, indent=2, ensure_ascii=False)
    print(f"Revisión guardada en {RUTA_REVISION}")