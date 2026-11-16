Normalización

Normalizar es organizar las tablas para que cada dato se guarde en un solo lugar. Si el mismo dato se repite en varias filas o tablas, una actualización puede dejar copias contradictorias.

No se deben guardar columnas que se pueden calcular a partir de otras tablas. Por ejemplo, el total de una venta no se guarda en la tabla venta, porque se obtiene sumando sus líneas en venta_producto; si se guardara, habría que mantenerlo sincronizado con cada cambio.

Cada columna debe depender de la clave primaria de su tabla y de nada más. Cuando una columna describe a otra entidad, como el nombre de la categoría de un producto, esa entidad merece su propia tabla.