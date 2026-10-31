# Registro de ensayos

## Ensayo de instalación limpia

- Fecha: 2026-10-24
- Alcance: clon desde GitHub en una carpeta nueva, con entorno virtual nuevo, en el mismo equipo de desarrollo.
- Encontrado: el README no incluía el paso de clonado del repositorio.
- Corregido: se agregó el paso de clonado al README y se confirmó que el resto de los pasos funciona siguiendo solo sus instrucciones.
- Resultado tras la corrección: instalación y ejecución de `python src/consumir_gemini.py` sin intervención manual, con respuesta real del modelo y sin errores. `git status` quedó limpio, `.env` no está versionado y no aparece en el historial.

## Ensayo de rate limit

- Fecha: 2026-10-31
- Peticiones enviadas: 30, secuenciales y sin espera entre llamadas (`python src/cliente.py` con el bucle de la lección). Una primera corrida con 10 peticiones no provocó el límite.
- Petición donde apareció el primer 429: la número 16 (la decimoséptima).
- Esperas observadas: 2,2 s y 4,1 s (backoff exponencial con jitter, correcto).
- Costo total del ensayo: USD 0,004590, con un registro por petición exitosa y ninguno por la petición fallida.
- Resultado: 29 de 30 peticiones con éxito. La petición 16 recibió 429 en sus tres intentos, agotó los reintentos y terminó en el `RuntimeError` del cliente, sin detener el ensayo.