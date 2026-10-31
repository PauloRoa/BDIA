import json
import os

from cliente import consultar_modelo
from pipeline_texto import CASOS, SYSTEM_INSTRUCTION, calcular_metricas, resumir_metricas

RUTA_RESULTADOS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "resultados_metricas.json"))


if __name__ == "__main__":
    resultados = []
    for caso in CASOS:
        try:
            respuesta = consultar_modelo(caso["pregunta"], system_instruction=SYSTEM_INSTRUCTION)
        except (ValueError, RuntimeError) as error:
            print(f"No se pudo obtener la respuesta a '{caso['pregunta']}': {error}")
            continue
        metricas = calcular_metricas(caso["referencia"], respuesta)
        resultados.append({
            "consulta": caso["pregunta"],
            "referencia": caso["referencia"],
            "respuesta": " ".join(respuesta.split()),
            **{nombre: round(valor, 3) for nombre, valor in metricas.items()},
        })
        with open(RUTA_RESULTADOS, "w", encoding="utf-8") as archivo:
            json.dump(resultados, archivo, indent=2, ensure_ascii=False)

    print("\nResumen:")
    for nombre, valor in resumir_metricas(resultados).items():
        print(f"  {nombre}: {valor:.3f}")

    print("\nCasos ordenados por F1, del peor al mejor:")
    for resultado in sorted(resultados, key=lambda r: r["f1"]):
        print(f"  {resultado['f1']:.3f}  {resultado['consulta']}")

    print(f"\nResultados guardados en {RUTA_RESULTADOS}")