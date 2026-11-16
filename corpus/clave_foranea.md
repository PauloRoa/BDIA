Clave foránea

Una clave foránea es una columna que referencia la clave primaria de otra tabla. Se declara con REFERENCES, por ejemplo cliente_id integer REFERENCES cliente(id), y PostgreSQL rechaza cualquier valor que no exista en la tabla referenciada.

La cláusula ON DELETE define qué ocurre con las filas hijas cuando se borra la fila padre: RESTRICT y NO ACTION impiden el borrado, CASCADE borra también las filas hijas y SET NULL deja la clave foránea en nulo. Se elige según el negocio: borrar un cliente no debería borrar en silencio su historial de ventas.

PostgreSQL no crea un índice automático sobre la clave foránea. Conviene crearlo cuando se consulta o se une con frecuencia por esa columna.