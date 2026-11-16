# Límites de autonomía del agente

Documento de supervisión del agente de borradores de bases de datos PostgreSQL (`src/agente_con_herramientas.py` y `src/agente_con_memoria.py`). Describe qué puede hacer el agente por sí solo, qué requiere aprobación humana y cómo se revisa su comportamiento.

## 1. Herramientas y nivel de riesgo

| Herramienta | Qué hace | Nivel | Consecuencia si falla o se usa mal |
|---|---|---|---|
| `consultar_buenas_practicas` | Devuelve una buena práctica fija sobre un tema, con ejemplo opcional. | Bajo | Una respuesta incompleta o irrelevante. No modifica nada. |
| `verificar_sentencias_permitidas` | Revisa si un script solo contiene `CREATE TABLE` y `CREATE INDEX`. | Bajo | Un informe incorrecto sobre el script. No modifica nada. |
| `guardar_borrador` | Escribe un script en `docs/borradores/<nombre>.sql`. | Alto | Crea archivos en disco y puede reemplazar uno existente. Como `docs/borradores/` está en `.gitignore`, un reemplazo no se puede recuperar desde Git. |

El agente no tiene ninguna herramienta de riesgo medio. Las demás acciones (ejecutar SQL, borrar archivos, conectarse a una base de datos) no existen como herramientas y el agente no puede realizarlas.

## 2. Herramientas que requieren aprobación humana

`guardar_borrador` siempre requiere aprobación humana. La aprobación está implementada en la propia herramienta (`esperar_aprobacion`, llamada desde `guardar_borrador`), de modo que no depende de que el agente la pida.

Controles previos a la aprobación (si fallan, no se pide aprobación y no se escribe nada):
- El nombre solo puede tener letras, números y guion bajo.
- El script no puede estar vacío.
- Todas las sentencias deben estar en la lista blanca: `CREATE TABLE` y `CREATE INDEX`.

Aprobación:
- Se muestra el nombre del archivo, la cantidad de sentencias y si se crea o se reemplaza un borrador existente.
- Solo la respuesta `s` aprueba. Cualquier otra respuesta, la ausencia de entrada o el vencimiento de los 60 segundos cuentan como rechazo.
- El rechazo es el valor por defecto: sin respuesta, no se escribe ningún archivo.
- Cada decisión se guarda en `registro_aprobaciones` (herramienta, nombre, si reemplaza, aprobado y momento UTC). La decisión también queda en la traza, porque la respuesta de la herramienta (aprobado o rechazado) se guarda como observación.

Evidencia real (sesión `supervision_riesgos`, 2026-11-16): `guardar_borrador` se ejecutó dos veces. En `ferreteria_demo` se respondió `s` y se creó el archivo. En `ferreteria_rechazo` se respondió `n`, no se creó ningún archivo y el agente informó al usuario que no se pudo completar el guardado.

## 3. Revisión de trazas

Cada consulta exitosa al agente agrega una línea a `docs/trazas_agente.jsonl` con: momento (UTC), sesión, entrada del usuario, acciones (herramienta, argumentos y observación) y respuesta final. Los turnos que fallan por error del modelo o de la red no se registran.

Traza de evidencia: 4 líneas, de las cuales 2 corresponden a herramientas de riesgo bajo y 2 a `guardar_borrador` (una aprobada y una rechazada).

Qué revisar y qué se considera sospechoso:
- Llamadas a `guardar_borrador` con rechazos repetidos, o intentos de guardar sentencias fuera de la lista blanca.
- Nombres de archivo inesperados o `reemplaza: true` que el usuario no pidió.
- Una `respuesta_final` que afirma un guardado cuando la observación dice que fue rechazado. La observación es la fuente confiable; la respuesta final la redacta el modelo.
- Muchas llamadas a herramientas en un solo turno o la misma llamada repetida.
- Consultas que debían usar una herramienta y tienen `acciones` vacías.

Cuándo revisar: después de cada sesión en la que se usó `guardar_borrador`, y de forma periódica sobre una muestra del resto de las líneas. Las líneas con herramientas de riesgo alto se revisan siempre completas.

## 4. Qué hacer ante un comportamiento inesperado

1. Detener la ejecución (Ctrl+C) y no responder ninguna aprobación pendiente.
2. Conservar `docs/trazas_agente.jsonl` sin editarla: es la evidencia.
3. Identificar en la traza la línea afectada: herramienta, argumentos y observación.
4. Revisar `docs/borradores/` para saber si se creó o reemplazó algún archivo y eliminar los no deseados.
5. Reproducir el caso con una prueba en `tests/test_agente.py` antes de corregir.
6. Corregir (por ejemplo, restringir la herramienta o ajustar la instrucción del agente) y ejecutar `python -m pytest`.
7. Volver a ejecutar el caso real y verificar en la traza que el comportamiento cambió.

## Límites conocidos

- Si vence el tiempo de aprobación, el hilo que espera la respuesta puede quedar bloqueado en `input()`, y la siguiente línea escrita podría llegar a ese hilo y no al nuevo. Tras un vencimiento conviene reiniciar el programa.
- `registro_aprobaciones` vive solo en memoria y se pierde al terminar el programa; el registro persistente de las decisiones es la observación guardada en la traza.
- La lista blanca se aplica obligatoriamente en `guardar_borrador`. En `verificar_sentencias_permitidas` solo se aplica si el agente decide usar esa herramienta.
- Una respuesta del modelo puede ser incorrecta aunque las herramientas funcionen bien; por eso las decisiones de riesgo alto no dependen del modelo.