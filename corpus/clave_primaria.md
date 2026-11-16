Clave primaria

Cada tabla debe tener una clave primaria que identifique cada fila de forma única. En PostgreSQL, la clave primaria no admite valores nulos ni repetidos y crea automáticamente un índice único sobre sus columnas.

Conviene usar una clave sustituta, como una columna de identidad (integer GENERATED ALWAYS AS IDENTITY) o serial, cuando ningún dato del negocio es estable y único. Datos como el correo o el RUT de un cliente pueden cambiar o repetirse por errores de ingreso, y una clave primaria no debe cambiar en el tiempo.

La clave primaria puede ser compuesta cuando la identidad de la fila depende de dos o más columnas, como ocurre en una tabla intermedia.