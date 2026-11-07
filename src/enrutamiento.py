import os

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable, RunnableBranch, RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI

from cadena_tres_pasos import DESCRIPCION_NEGOCIO, construir_cadena
from consumir_gemini import MODELO

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


def construir_paso_clasificacion(modelo) -> Runnable:
    return (
        PLANTILLA_CLASIFICAR
        | modelo
        | StrOutputParser()
        | (lambda texto: texto.strip().lower())
    )


def construir_cadena_rechazo(modelo) -> Runnable:
    return PLANTILLA_RECHAZAR | modelo | StrOutputParser()


def construir_cadena_aclaracion(modelo) -> Runnable:
    return PLANTILLA_ACLARAR | modelo | StrOutputParser()


def construir_cadena_con_enrutamiento(
    paso_clasificacion,
    cadena_nueva=None,
    cadena_existente=None,
    cadena_aclaracion=None,
) -> Runnable:
    cadena_nueva = cadena_nueva or RunnablePassthrough()
    cadena_existente = cadena_existente or RunnablePassthrough()
    cadena_aclaracion = cadena_aclaracion or RunnablePassthrough()

    bifurcacion = RunnableBranch(
        (lambda x: x["categoria"] == "nueva", cadena_nueva),
        (lambda x: x["categoria"] == "existente", cadena_existente),
        cadena_aclaracion,
    )

    return RunnablePassthrough.assign(categoria=paso_clasificacion) | bifurcacion


if __name__ == "__main__":
    load_dotenv()
    modelo = ChatGoogleGenerativeAI(
        model=MODELO,
        google_api_key=os.getenv("API_KEY"),
        temperature=0,
    )
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=construir_paso_clasificacion(modelo),
        cadena_nueva=construir_cadena(modelo),
        cadena_existente=construir_cadena_rechazo(modelo),
        cadena_aclaracion=construir_cadena_aclaracion(modelo),
    )

    solicitudes = [
        DESCRIPCION_NEGOCIO,
        "Agrega una columna de correo a la tabla de clientes de mi base actual.",
        "¿Qué diferencia hay entre una clave primaria y una clave foránea?",
    ]
    for solicitud in solicitudes:
        print(f"Solicitud: {solicitud}\n")
        print(cadena.invoke({"descripcion": solicitud}))
        print("\n" + "-" * 60 + "\n")