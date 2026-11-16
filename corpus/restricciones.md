Restricciones de integridad

Las restricciones hacen que PostgreSQL rechace datos inválidos antes de que entren a la tabla. NOT NULL obliga a que la columna tenga valor y se usa en los datos que el negocio exige siempre, como el nombre de un cliente.

UNIQUE impide valores repetidos en columnas que no son la clave primaria, como el correo de un cliente. CHECK valida una condición sobre la fila, por ejemplo CHECK (precio >= 0) o CHECK (cantidad > 0).

DEFAULT asigna un valor cuando no se informa uno, como DEFAULT now() en la fecha de creación de una venta. Cuando la descripción del negocio no indica si un dato es obligatorio, conviene no agregar NOT NULL y marcar la decisión como supuesto.