# Límites de la métrica de evaluación

## Qué mide

Qué proporción de palabras comparten la respuesta del modelo y una referencia propia, tras normalizar el texto y contando cada palabra repetida como máximo tantas veces como aparezca en el texto donde menos se repite, expresada como precisión (sobre la respuesta), cobertura (sobre la referencia) y F1 (ambas combinadas).

## Modos de falla conocidos

Observados en la revisión manual (`docs/revision_manual.json`):

- **Una respuesta correcta dicha con otras palabras obtiene un F1 bajo.** El caso 18 (ON DELETE CASCADE) tuvo el F1 más bajo de los 20, 0,261, y es correcto y completo: habla de "registros" y de una "tabla padre" y una "tabla hija" donde la referencia dice "filas" y "las filas que referencian a una fila". Los casos 14, 19 y 2 muestran lo mismo (F1 entre 0,388 y 0,471).
- **Agregar contenido correcto baja la precisión.** En los 20 casos, la precisión promedio fue 0,516 y la cobertura 0,788: las respuestas incluyen lo que dice la referencia, pero suman explicaciones válidas, como "dependencias transitivas" (caso 14) o "integridad referencial" (caso 2).
- **Ordenar por F1 no ordena por calidad.** El caso 11 (índice), que omite el costo en espacio y escrituras y es el único calificado como parcialmente completo, tuvo un F1 de 0,452, mayor que los casos 18 (0,261) y 14 (0,388), que están completos.

Posibles, aunque no aparecieron en esta muestra (comprobados en `tests/test_pipeline_texto.py`):

- **Un dato incorrecto puede mantener un F1 alto.** "El tipo INTEGER ocupa 4 bytes" frente a "ocupa 8 bytes" da 0,875. En la muestra, los datos de los casos 4 a 7 eran correctos.
- **Quitar una negación casi no cambia el F1, aunque invierte el sentido.** "Una clave primaria no puede contener valores nulos" frente a "puede contener valores nulos" da 0,933.

## Muestra revisada

- 2026-10-31: 10 de 20 respuestas de `gemini-3.1-flash-lite`, generadas con `src/evaluar_salidas.py` (`docs/resultados_metricas.json`). Se tomaron los 5 casos con menor F1 (18, 14, 11, 19 y 2) y los 5 con mayor F1 (4, 5, 6, 15 y 7), y se calificaron según corrección factual, completitud y contradicción. Resultado: las 10 son correctas, ninguna contradice su referencia y una (caso 11) la cubre solo en parte.

## Recomendación de uso

En este proyecto, el F1 solo sirve para detectar cambios entre versiones del prompt o del cliente sobre los 20 casos de `src/evaluar_salidas.py`, y toda respuesta con cifras, tipos de datos o un sí o no se lee a mano, sin importar su F1.