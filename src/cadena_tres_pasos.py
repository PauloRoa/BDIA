import os

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from consumir_gemini import MODELO

DESCRIPCION_NEGOCIO = (
    "Una ferretería de barrio vende productos a clientes registrados. "
    "Cada producto tiene código, nombre, categoría, precio y stock. "
    "Cada venta tiene fecha, cliente y uno o más productos con su cantidad "
    "y precio de venta."
)

# Paso 1: identifica entidades, atributos y relaciones, sin proponer tablas.
PLANTILLA_EXTRAER = PromptTemplate.from_template(
    "Lee la siguiente descripción de un negocio e identifica sus entidades, "
    "los atributos de cada una y las relaciones entre ellas, indicando si son "
    "uno a muchos o muchos a muchos. No propongas tablas ni tipos de datos. "
    "Incluye los atributos que la descripción menciona. Puedes sugerir "
    "atributos habituales para una entidad, pero márcalos como supuesto. "
    "Responde solo con la lista, sin introducción ni formato markdown."
    "\n\nDescripción:\n{descripcion}"
)

# Paso 2: convierte las entidades en tablas con columnas, tipos y claves.
PLANTILLA_MODELAR = PromptTemplate.from_template(
    "A partir de estas entidades y relaciones, define las tablas de una base "
    "de datos relacional en PostgreSQL. Para cada tabla indica sus columnas con "
    "su tipo de dato, la clave primaria y las claves foráneas. Resuelve cada "
    "relación muchos a muchos con una tabla intermedia. Mantén la marca de "
    "supuesto en las columnas que la tengan. No agregues columnas que se puedan "
    "calcular a partir de otras tablas. No escribas SQL. Responde solo con la "
    "definición de las tablas, sin introducción ni formato markdown."
    "\n\nEntidades y relaciones:\n{entidades}"
)

# Paso 3: escribe el script CREATE TABLE en el orden que exigen las claves foráneas.
PLANTILLA_GENERAR = PromptTemplate.from_template(
    "Escribe el script SQL de PostgreSQL que crea estas tablas, usando solo "
    "sentencias CREATE TABLE con claves primarias, claves foráneas y "
    "restricciones NOT NULL donde corresponda. Si una columna está marcada como "
    "supuesto, no le pongas NOT NULL y escribe el comentario SQL -- supuesto "
    "después de la coma que la separa de la columna siguiente, nunca en lugar "
    "de esa coma. Ordena las sentencias para que cada tabla se cree después de "
    "las tablas que referencia. Responde solo con el SQL, sin explicaciones ni "
    "bloques de código markdown."
    "\n\nTablas:\n{tablas}"
)


def construir_cadena(modelo):
    paso_extraer = PLANTILLA_EXTRAER | modelo | StrOutputParser()
    paso_modelar = PLANTILLA_MODELAR | modelo | StrOutputParser()
    paso_generar = PLANTILLA_GENERAR | modelo | StrOutputParser()

    return (
        paso_extraer
        | (lambda entidades: {"entidades": entidades})
        | paso_modelar
        | (lambda tablas: {"tablas": tablas})
        | paso_generar
    )


if __name__ == "__main__":
    load_dotenv()
    modelo = ChatGoogleGenerativeAI(
        model=MODELO,
        google_api_key=os.getenv("API_KEY"),
        temperature=0,
        timeout=60,
    )
    cadena = construir_cadena(modelo)
    resultado = cadena.invoke({"descripcion": DESCRIPCION_NEGOCIO})
    print(resultado)