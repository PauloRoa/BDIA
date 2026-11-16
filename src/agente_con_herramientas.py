import logging
import os
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from consumir_gemini import MODELO
from enrutamiento import (
    MENSAJE_ERROR_CONFIGURACION,
    MENSAJE_ERROR_GENERAL,
    es_error_de_configuracion,
)

logger = logging.getLogger(__name__)

BUENAS_PRACTICAS = {
    "clave primaria": (
        "Cada tabla tiene una clave primaria que identifica cada fila de forma "
        "única y que no cambia en el tiempo."
    ),
    "clave foránea": (
        "Una clave foránea referencia la clave primaria de otra tabla y asegura "
        "que cada relación apunte a una fila que existe."
    ),
    "muchos a muchos": (
        "Una relación muchos a muchos se resuelve con una tabla intermedia que "
        "guarda las claves foráneas de las dos tablas relacionadas."
    ),
    "normalización": (
        "Cada dato se guarda en un solo lugar: no se repiten datos ni se "
        "almacenan columnas que se pueden calcular a partir de otras tablas."
    ),
    "tipo de dato": (
        "Cada columna usa el tipo más ajustado a su contenido: numeric para "
        "montos, integer para cantidades y timestamp para fechas con hora."
    ),
}

EJEMPLOS = {
    "clave primaria": (
        "en una tabla cliente, la columna id serial PRIMARY KEY identifica a "
        "cada cliente aunque dos tengan el mismo nombre."
    ),
    "clave foránea": (
        "en una tabla venta, cliente_id integer REFERENCES cliente(id) impide "
        "registrar una venta de un cliente que no existe."
    ),
    "muchos a muchos": (
        "una venta incluye varios productos y un producto aparece en varias "
        "ventas, así que la tabla venta_producto guarda venta_id y producto_id, "
        "con la cantidad y el precio de cada línea."
    ),
    "normalización": (
        "el total de una venta no se guarda en la tabla venta, porque se "
        "calcula sumando sus líneas en venta_producto."
    ),
    "tipo de dato": (
        "el precio de un producto se guarda como numeric(10,2) y no como real, "
        "para evitar errores de redondeo en los montos."
    ),
}

SENTENCIAS_PERMITIDAS = ("CREATE TABLE", "CREATE INDEX")

CARPETA_BORRADORES = Path(__file__).resolve().parents[1] / "docs" / "borradores"
TIEMPO_LIMITE_APROBACION = 60

registro_aprobaciones = []


def revisar_sentencias(script):
    sentencias = [sentencia.strip() for sentencia in script.split(";")]
    sentencias = [sentencia for sentencia in sentencias if sentencia]
    no_permitidas = [
        sentencia
        for sentencia in sentencias
        if not sentencia.upper().startswith(SENTENCIAS_PERMITIDAS)
    ]
    return sentencias, no_permitidas


def esperar_aprobacion(mensaje: str, tiempo_limite_segundos: int = 15) -> bool:
    cola_respuesta = queue.Queue()

    def pedir_entrada():
        try:
            texto = input(mensaje)
            cola_respuesta.put(texto.strip().lower())
        except (EOFError, KeyboardInterrupt):
            cola_respuesta.put("")

    hilo = threading.Thread(target=pedir_entrada, daemon=True)
    hilo.start()

    try:
        respuesta = cola_respuesta.get(timeout=tiempo_limite_segundos)
        return respuesta == "s"
    except queue.Empty:
        print("Tiempo de espera agotado: la acción queda rechazada.")
        return False


def registrar_aprobacion(herramienta: str, argumentos: dict, aprobado: bool) -> None:
    registro_aprobaciones.append(
        {
            "herramienta": herramienta,
            "argumentos": argumentos,
            "aprobado": aprobado,
            "momento": datetime.now(timezone.utc).isoformat(),
        }
    )


class ArgumentosBuenasPracticas(BaseModel):
    tema: str = Field(
        description=(
            "Tema de modelado sobre el que se pregunta, por ejemplo "
            "'muchos a muchos' o 'clave foránea'."
        ),
    )
    incluir_ejemplo: bool = Field(
        default=False,
        description=(
            "Si es True, agrega un ejemplo de modelado del tema, no solo la "
            "buena práctica."
        ),
    )


class ArgumentosGuardarBorrador(BaseModel):
    nombre: str = Field(
        description=(
            "Nombre del borrador, solo con letras, números y guion bajo, sin "
            "extensión, por ejemplo 'ferreteria_ventas'."
        ),
    )
    script: str = Field(
        description="Script SQL completo que se guarda como borrador.",
    )


@tool("consultar_buenas_practicas", args_schema=ArgumentosBuenasPracticas)
def consultar_buenas_practicas(tema: str, incluir_ejemplo: bool = False) -> str:
    """Devuelve la buena práctica de modelado de bases de datos relacionales
    sobre un tema, como clave primaria, clave foránea, muchos a muchos,
    normalización o tipo de dato, con un ejemplo si se pide. Usar cuando el
    usuario pregunta cómo o por qué se modela algo de cierta forma."""
    for clave, practica in BUENAS_PRACTICAS.items():
        if clave in tema.lower():
            if incluir_ejemplo:
                return f"{practica} Ejemplo: {EJEMPLOS[clave]}"
            return practica
    return "No hay una buena práctica registrada para ese tema."


@tool
def verificar_sentencias_permitidas(script: str) -> str:
    """Revisa si un script SQL usa solo las sentencias que el servicio permite:
    CREATE TABLE y CREATE INDEX. Usar cuando el usuario entrega un script SQL
    y pregunta si cumple las reglas del servicio."""
    sentencias, no_permitidas = revisar_sentencias(script)
    if not sentencias:
        return "El script no contiene sentencias."
    if no_permitidas:
        return "El script contiene sentencias no permitidas: " + "; ".join(
            no_permitidas
        )
    return f"El script cumple: sus {len(sentencias)} sentencias están permitidas."


@tool("guardar_borrador", args_schema=ArgumentosGuardarBorrador)
def guardar_borrador(nombre: str, script: str) -> str:
    """Guarda un script SQL como borrador en docs/borradores. Si ya existe un
    borrador con ese nombre, lo reemplaza y la versión anterior se pierde:
    acción irreversible que requiere aprobación humana antes de ejecutarse.
    Usar solo cuando el usuario pide guardar un script."""
    if not nombre.replace("_", "").isalnum():
        return (
            "No se guardó: el nombre solo puede tener letras, números y "
            "guion bajo."
        )
    sentencias, no_permitidas = revisar_sentencias(script)
    if not sentencias:
        return "No se guardó: el script no contiene sentencias."
    if no_permitidas:
        return "No se guardó: el script contiene sentencias no permitidas: " + (
            "; ".join(no_permitidas)
        )

    ruta = CARPETA_BORRADORES / f"{nombre}.sql"
    reemplaza = ruta.exists()
    accion = "reemplazar el borrador existente" if reemplaza else "crear el borrador"
    mensaje = (
        f"[SUPERVISIÓN HUMANA] El agente quiere {accion} '{nombre}.sql' con "
        f"{len(sentencias)} sentencias. ¿Aprobar? (s/n): "
    )
    aprobado = esperar_aprobacion(mensaje, TIEMPO_LIMITE_APROBACION)
    registrar_aprobacion(
        herramienta="guardar_borrador",
        argumentos={"nombre": nombre, "reemplaza": reemplaza},
        aprobado=aprobado,
    )
    if not aprobado:
        return (
            "Guardado rechazado por el supervisor humano o sin respuesta a "
            "tiempo: no se escribió ningún archivo."
        )

    CARPETA_BORRADORES.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(script)
    if reemplaza:
        return (
            f"Guardado aprobado por el supervisor humano: se reemplazó el "
            f"borrador '{nombre}.sql'."
        )
    return (
        f"Guardado aprobado por el supervisor humano: se creó el borrador "
        f"'{nombre}.sql'."
    )


HERRAMIENTAS = [
    consultar_buenas_practicas,
    verificar_sentencias_permitidas,
    guardar_borrador,
]

INSTRUCCION_SISTEMA = (
    "Eres un asistente de diseño de bases de datos relacionales en PostgreSQL. "
    "Usa las herramientas disponibles cuando las necesites y apóyate en lo que "
    "devuelven. Responde en español, en no más de tres oraciones y sin formato "
    "markdown."
)

PROMPT_AGENTE = ChatPromptTemplate.from_messages(
    [
        ("system", INSTRUCCION_SISTEMA),
        ("human", "{entrada}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)


def construir_agente(modelo, prompt=PROMPT_AGENTE):
    agente = create_tool_calling_agent(modelo, HERRAMIENTAS, prompt)
    return AgentExecutor(
        agent=agente,
        tools=HERRAMIENTAS,
        verbose=True,
        return_intermediate_steps=True,
    )


def herramientas_usadas(resultado):
    return [accion.tool for accion, observacion in resultado["intermediate_steps"]]


def texto_de_salida(salida):
    if isinstance(salida, str):
        return salida
    return "".join(bloque["text"] for bloque in salida if bloque.get("type") == "text")


def consultar_agente_seguro(ejecutor_agente, entrada):
    try:
        resultado = ejecutor_agente.invoke({"entrada": entrada})
    except Exception as error:
        logger.exception("Error consultando al agente")
        if es_error_de_configuracion(error):
            return MENSAJE_ERROR_CONFIGURACION, None
        return MENSAJE_ERROR_GENERAL, None
    return texto_de_salida(resultado["output"]), herramientas_usadas(resultado)


VERIFICACIONES = [
    (
        "¿Por qué una relación muchos a muchos necesita una tabla intermedia?",
        "consultar_buenas_practicas",
    ),
    (
        "¿Este script cumple las sentencias permitidas? "
        "CREATE TABLE cliente (id serial PRIMARY KEY); DROP TABLE venta;",
        "verificar_sentencias_permitidas",
    ),
    ("¿Qué es PostgreSQL?", None),
]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    modelo = ChatGoogleGenerativeAI(
        model=MODELO,
        google_api_key=os.getenv("API_KEY"),
        temperature=0,
        timeout=60,
    )
    ejecutor_agente = construir_agente(modelo)

    for entrada, herramienta_esperada in VERIFICACIONES:
        respuesta, herramientas = consultar_agente_seguro(ejecutor_agente, entrada)
        print(f"Entrada: {entrada}")
        print(f"Respuesta: {respuesta}")
        if herramientas is None:
            print("Verificación no realizada: la consulta falló.\n")
            continue
        print(f"Herramientas usadas: {herramientas}\n")
        if herramienta_esperada is None:
            assert herramientas == []
        else:
            assert herramienta_esperada in herramientas