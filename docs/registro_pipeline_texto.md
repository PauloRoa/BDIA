# Registro del pipeline de texto

Coincidencia por palabras entre una referencia propia y la respuesta del modelo, calculada sobre texto crudo y sobre texto procesado con `procesar_texto`.

## Caso 1

- Pregunta: ¿Qué es una clave primaria en una base de datos relacional?
- Referencia: Una clave primaria es una columna o conjunto de columnas que identifica de forma única cada fila de una tabla.
- Respuesta: Una clave primaria es un campo o conjunto de campos que identifica de manera única e irrepetible cada registro dentro de una tabla en una base de datos relacional.
- Coincidencia texto crudo: 70.6%
- Coincidencia texto procesado: 75.0%

## Caso 2

- Pregunta: ¿Qué es una clave foránea en una base de datos relacional?
- Referencia: Una clave foránea es una columna que referencia la clave primaria de otra tabla para relacionar ambas tablas.
- Respuesta: Una clave foránea es un campo o conjunto de campos en una tabla que establece un vínculo lógico con la clave primaria de otra tabla, garantizando así la integridad referencial entre ambas.
- Coincidencia texto crudo: 64.7%
- Coincidencia texto procesado: 68.8%

## Caso 3

- Pregunta: ¿Qué es la normalización de una base de datos relacional?
- Referencia: La normalización es el proceso de organizar las tablas de una base de datos para reducir la redundancia y evitar anomalías al modificar los datos.
- Respuesta: La normalización es el proceso de organizar los datos en una base de datos para reducir la redundancia y mejorar la integridad de la información mediante la aplicación de reglas llamadas formas normales.
- Coincidencia texto crudo: 69.6%
- Coincidencia texto procesado: 71.4%
