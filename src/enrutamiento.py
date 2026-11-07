import logging
import os

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    RunnableBranch,
    RunnableLambda,
    RunnablePassthrough,
)
from langchain_google_genai import ChatGoogleGenerativeAI

from cadena_tres_pasos import DESCRIPCION_NEGOCIO, construir_cadena
from consumir_gemini import MODELO
from pipeline_texto import limpiar_texto

logger = logging.getLogger(__name__)

MENSAJE_RESPALDO_NUEVA = (
    "No pudimos generar el borrador de la base de datos en este momento por un "
    "problema con el servicio de generación. Intenta de nuevo en unos minutos."
)
MENSAJE_RESPALDO_EXISTENTE = (
    "Este servicio solo diseña bases de datos nuevas a partir de la descripción "
    "de un negocio; no modifica, migra ni analiza bases existentes. Describe tu "
    "negocio para obtener el diseño de una base nueva."
)
MENSAJE_RESPALDO_ACLARACION = (
    "Para diseñar una base de datos necesito una descripción de tu negocio: qué "
    "registra y qué datos tiene cada cosa. Por ejemplo: una tienda que registra "
    "productos con su nombre y precio, y ventas con su fecha y cliente."
)
MENSAJE_ERROR_GENERAL = (
    "No pudimos procesar tu solicitud en este momento. Intenta de nuevo más tarde."
)
MENSAJE_ERROR_CONFIGURACION = (
    "El servicio no está disponible por un problema de configuración. "
    "El error quedó registrado para el administrador."
)

# Clasificación: decide si la solicitud está dentro del alcance del servicio.
PLANTILLA_CLASIFICAR = PromptTemplate.from_template(
    "Clasifica la siguiente solicitud en una sola palabra: nueva, si describe "
    "un negocio para diseñar una base de datos nueva; existente, si pide "
    "modificar, migrar o analizar una base de datos que ya existe; otra, en "
    "cualquier otro caso. Responde solo con esa palabra."
    "\n\nSolicitud:\n{descripcion}"
)

# Ruta existente: rechaza la solicitud y explica el alcance del servicio.
PLANTILLA_RECHAZAR = PromptTemplate.from_template(
    "Este servicio solo diseña bases de datos nuevas a partir de la descripción "
    "de un negocio; no modifica, migra ni analiza bases existentes. Responde a "
    "la siguiente solicitud en dos oraciones: explica que está fuera de ese "
    "alcance y sugiere cómo reformularla como el diseño de una base nueva. "
    "Responde sin formato markdown.\n\nSolicitud:\n{descripcion}"
)

# Ruta por defecto: pide una descripción del negocio.
PLANTILLA_ACLARAR = PromptTemplate.from_template(
    "La siguiente solicitud no describe un negocio para diseñar una base de "
    "datos. Responde en dos oraciones: indica que el servicio necesita una "
    "descripción del negocio y da un ejemplo breve de qué información incluir, "
    "como qué registra el negocio y qué datos tiene cada cosa. Responde sin "
    "formato markdown.\n\nSolicitud:\n{descripcion}"
)


def construir_paso_clasificacion(modelo):
    return (
        PLANTILLA_CLASIFICAR
        | modelo
        | StrOutputParser()
        | (lambda texto: limpiar_texto(texto).strip())
    )


def construir_cadena_rechazo(modelo):
    return PLANTILLA_RECHAZAR | modelo | StrOutputParser()


def construir_cadena_aclaracion(modelo):
    return PLANTILLA_ACLARAR | modelo | StrOutputParser()


def construir_ruta_segura(cadena, mensaje_respaldo):
    def responder_con_respaldo(entrada):
        logger.warning("La ruta falló y se usó el mensaje de respaldo")
        return mensaje_respaldo

    return cadena.with_fallbacks([RunnableLambda(responder_con_respaldo)])


def construir_cadena_con_enrutamiento(
    paso_clasificacion,
    cadena_nueva=None,
    cadena_existente=None,
    cadena_aclaracion=None,
):
    cadena_nueva = cadena_nueva or RunnablePassthrough()
    cadena_existente = cadena_existente or RunnablePassthrough()
    cadena_aclaracion = cadena_aclaracion or RunnablePassthrough()

    bifurcacion = RunnableBranch(
        (lambda x: x["categoria"] == "nueva", cadena_nueva),
        (lambda x: x["categoria"] == "existente", cadena_existente),
        cadena_aclaracion,
    )

    return RunnablePassthrough.assign(categoria=paso_clasificacion) | bifurcacion


def es_error_de_configuracion(error: Exception) -> bool:
    return "API_KEY_INVALID" in str(error)


def procesar_solicitud_segura(cadena, descripcion: str) -> str:
    try:
        if not descripcion.strip():
            return MENSAJE_RESPALDO_ACLARACION
        return cadena.invoke({"descripcion": descripcion})
    except Exception as error:
        logger.exception("Error procesando la solicitud")
        if es_error_de_configuracion(error):
            return MENSAJE_ERROR_CONFIGURACION
        return MENSAJE_ERROR_GENERAL


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    modelo = ChatGoogleGenerativeAI(
        model=MODELO,
        google_api_key=os.getenv("API_KEY"),
        temperature=0,
        timeout=60,
    )
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=construir_paso_clasificacion(modelo),
        cadena_nueva=construir_ruta_segura(
            construir_cadena(modelo), MENSAJE_RESPALDO_NUEVA
        ),
        cadena_existente=construir_ruta_segura(
            construir_cadena_rechazo(modelo), MENSAJE_RESPALDO_EXISTENTE
        ),
        cadena_aclaracion=construir_ruta_segura(
            construir_cadena_aclaracion(modelo), MENSAJE_RESPALDO_ACLARACION
        ),
    )

    solicitudes = [
        DESCRIPCION_NEGOCIO,
        "Agrega una columna de correo a la tabla de clientes de mi base actual.",
        "¿Qué diferencia hay entre una clave primaria y una clave foránea?",
    ]
    for solicitud in solicitudes:
        print(f"Solicitud: {solicitud}\n")
        print(procesar_solicitud_segura(cadena, solicitud))
        print("\n" + "-" * 60 + "\n")