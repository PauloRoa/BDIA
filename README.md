# Proyecto BDIA

Repositorio del proyecto de la especialización en IA (Skillnest / Accenture). Estado actual: Unidad U1.2, setup técnico (repositorio, entorno virtual, variables de entorno y primera petición autenticada a una API de modelo).

## Requisitos

- Python 3.13 (probado con 3.13.0)
- Git
- Una API key de Google Gemini, creada en Google AI Studio

## Puesta en marcha

1. Crear el entorno virtual:

```
python -m venv .venv
```

2. Activarlo (cada terminal necesita su propia activación):

Git Bash:

```
source .venv/Scripts/activate
```

PowerShell:

```
.\.venv\Scripts\Activate.ps1
```

3. Instalar las dependencias:

```
pip install -r requirements.txt
```

4. Crear el archivo de variables de entorno a partir de la plantilla:

```
cp .env.example .env
```

5. Abrir `.env` y reemplazar el marcador por tu clave real en la variable `API_KEY`. El archivo `.env` está excluido en `.gitignore` y nunca se sube al repositorio.

## Estructura

- `src/`: código fuente.
- `docs/`: documentación y evidencias. Incluye la evidencia de la primera petición autenticada (`evidencia_peticion_autenticada.txt` y `.png`).
- `tests/`: pruebas.
- `requirements.txt`: dependencias de Python.
- `.env.example`: plantilla de variables de entorno, sin valores reales.

## Reglas de seguridad

- Ningún secreto (clave de API, token) se escribe en el código ni en archivos versionados.
- Las claves viven solo en `.env`.