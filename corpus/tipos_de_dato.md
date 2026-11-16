Tipos de dato

Cada columna debe usar el tipo más ajustado a su contenido. Los montos de dinero se guardan como numeric(10,2) y no como real ni double precision, porque los tipos de punto flotante producen errores de redondeo. Las cantidades enteras usan integer, o bigint si pueden superar los dos mil millones.

Las fechas con hora se guardan como timestamp, o timestamptz si se necesita la zona horaria, y las fechas sin hora como date. Los textos de largo variable usan text o varchar(n); en PostgreSQL no hay diferencia de rendimiento entre ambos, y varchar(n) solo se usa cuando el negocio exige un largo máximo.

No se deben guardar fechas ni números como texto, porque se pierde la validación y el orden correcto.