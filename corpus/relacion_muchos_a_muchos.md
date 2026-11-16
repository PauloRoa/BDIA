Relación muchos a muchos

Una relación muchos a muchos no se puede representar con una sola clave foránea. Se resuelve con una tabla intermedia que guarda las claves foráneas de las dos tablas relacionadas. Por ejemplo, una venta incluye varios productos y un producto aparece en varias ventas, así que la tabla venta_producto guarda venta_id y producto_id.

La clave primaria de la tabla intermedia suele ser compuesta por esas dos columnas, lo que impide repetir el mismo par. Si la relación tiene datos propios, como la cantidad o el precio de cada línea, esos atributos se guardan en la tabla intermedia y no en ninguna de las dos tablas originales.