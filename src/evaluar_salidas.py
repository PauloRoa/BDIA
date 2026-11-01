import json
import os
import time

from cliente import consultar_modelo
from pipeline_texto import CASOS, SYSTEM_INSTRUCTION, calcular_metricas, resumir_metricas

RUTA_RESULTADOS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "resultados_metricas.json"))

PAUSA_ENTRE_LLAMADAS = 2
TAMANO_MUESTRA = 5

CASOS_EVALUACION = CASOS + [
    {"pregunta": "¿Cuántos bytes ocupa el tipo INTEGER en PostgreSQL?", "referencia": "El tipo INTEGER ocupa 4 bytes en PostgreSQL."},
    {"pregunta": "¿Cuántos bytes ocupa el tipo BIGINT en PostgreSQL?", "referencia": "El tipo BIGINT ocupa 8 bytes en PostgreSQL."},
    {"pregunta": "¿Quién propuso el modelo relacional y en qué año?", "referencia": "Edgar F. Codd propuso el modelo relacional en 1970."},
    {"pregunta": "¿Cuál es la longitud máxima de un identificador en PostgreSQL?", "referencia": "La longitud máxima de un identificador en PostgreSQL es de 63 bytes."},
    {"pregunta": "¿Qué tipo de índice crea PostgreSQL por defecto?", "referencia": "PostgreSQL crea por defecto un índice de tipo B-tree."},
    {"pregunta": "¿Puede una clave primaria contener valores nulos?", "referencia": "No, una clave primaria no puede contener valores nulos."},
    {"pregunta": "¿Puede una tabla tener más de una clave primaria?", "referencia": "No, una tabla solo puede tener una clave primaria, aunque esta puede estar formada por varias columnas."},
    {"pregunta": "¿Qué es un índice en una base de datos relacional?", "referencia": "Un índice es una estructura que acelera la búsqueda de filas en una tabla a cambio de espacio adicional y escrituras más lentas."},
    {"pregunta": "¿Qué exige la primera forma normal?", "referencia": "La primera forma normal exige que cada columna contenga valores atómicos y que no existan grupos repetidos."},
    {"pregunta": "¿Qué exige la segunda forma normal?", "referencia": "La segunda forma normal exige cumplir la primera y que ninguna columna dependa solo de una parte de la clave primaria."},
    {"pregunta": "¿Qué exige la tercera forma normal?", "referencia": "La tercera forma normal exige cumplir la segunda y que ninguna columna dependa de otra columna que no sea clave."},
    {"pregunta": "¿Cómo se representa una relación de muchos a muchos en un modelo relacional?", "referencia": "Una relación de muchos a muchos se representa con una tabla intermedia que contiene las claves foráneas de ambas tablas."},
    {"pregunta": "¿Dónde se ubica la clave foránea en una relación de uno a muchos?", "referencia": "En una relación de uno a muchos, la clave foránea se ubica en la tabla del lado de muchos."},
    {"pregunta": "¿Qué tipo de dato se recomienda en PostgreSQL para almacenar montos de dinero?", "referencia": "Se recomienda NUMERIC, porque almacena valores decimales exactos sin errores de redondeo."},
    {"pregunta": "¿Qué hace la opción ON DELETE CASCADE en una clave foránea?", "referencia": "ON DELETE CASCADE elimina automáticamente las filas que referencian a una fila cuando esta se elimina."},
    {"pregunta": "¿Qué es una restricción CHECK en PostgreSQL?", "referencia": "Una restricción CHECK valida que los valores de una columna cumplan una condición antes de guardarlos."},
    {"pregunta": "¿Qué es un diccionario de datos?", "referencia": "Un diccionario de datos es un documento que describe las tablas, columnas, tipos de datos y restricciones de una base de datos."},
]


if __name__ == "__main__":
    resultados = []
    for numero, caso in enumerate(CASOS_EVALUACION, start=1):
        if numero > 1:
            time.sleep(PAUSA_ENTRE_LLAMADAS)
        try:
            respuesta = consultar_modelo(caso["pregunta"], system_instruction=SYSTEM_INSTRUCTION)
        except (ValueError, RuntimeError) as error:
            print(f"[Caso {numero}] No se pudo obtener la respuesta: {error}")
            continue
        metricas = calcular_metricas(caso["referencia"], respuesta)
        resultados.append({
            "caso": numero,
            "consulta": caso["pregunta"],
            "referencia": caso["referencia"],
            "respuesta": " ".join(respuesta.split()),
            **{nombre: round(valor, 3) for nombre, valor in metricas.items()},
        })
        with open(RUTA_RESULTADOS, "w", encoding="utf-8") as archivo:
            json.dump(resultados, archivo, indent=2, ensure_ascii=False)

    print(f"\nRespuestas evaluadas: {len(resultados)} de {len(CASOS_EVALUACION)}")

    print("\nResumen:")
    for nombre, valor in resumir_metricas(resultados).items():
        print(f"  {nombre}: {valor:.3f}")

    ordenados = sorted(resultados, key=lambda r: r["f1"])
    print(f"\nMuestra para revisar a mano ({TAMANO_MUESTRA} con menor F1 y {TAMANO_MUESTRA} con mayor F1):")
    for resultado in ordenados[:TAMANO_MUESTRA] + ordenados[-TAMANO_MUESTRA:]:
        print(f"  Caso {resultado['caso']:>2}  F1 {resultado['f1']:.3f}  {resultado['consulta']}")

    print(f"\nResultados guardados en {RUTA_RESULTADOS}")