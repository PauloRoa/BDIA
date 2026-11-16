Índices

Un índice acelera las búsquedas sobre una columna a costa de ocupar espacio y de hacer más lentas las escrituras, porque cada inserción o actualización debe mantenerlo. Se crea con CREATE INDEX nombre ON tabla (columna).

La clave primaria y las restricciones UNIQUE ya crean su propio índice, así que no se deben duplicar. Conviene indexar las claves foráneas y las columnas que se usan con frecuencia en WHERE o en JOIN.

No conviene indexar tablas muy pequeñas ni columnas con pocos valores distintos, como un indicador de verdadero o falso, porque el índice rara vez se usa.