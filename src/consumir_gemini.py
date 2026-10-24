import os
import requests
from dotenv import load_dotenv

load_dotenv()

#Constantes
API_KEY = os.getenv("API_KEY")
MODELO = "gemini-3.1-flash-lite"
URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"
    


def armar_peticion(prompt, modelo=MODELO):
    if not prompt:
        raise ValueError("La pregunta no puede estar vacía.")
    url = f"{URL_BASE}{modelo}:generateContent"
    headers = {"x-goog-api-key": API_KEY}
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    return url, headers, body


def enviar_peticion(url, headers, body):
    try:
        respuesta = requests.post(url, headers=headers, json=body, timeout=60)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as error_conexion:
        raise RuntimeError(f"No se pudo conectar con el servicio o se agotó el tiempo de espera: {error_conexion}")
    try:
        respuesta_json = respuesta.json()
    except requests.exceptions.JSONDecodeError as error_formato:
        raise RuntimeError(f"La respuesta del servicio no llegó en el formato esperado: {error_formato}")
    if "error" in respuesta_json:
        raise RuntimeError(f"El servicio rechazó la petición: {respuesta_json['error']['message']}")
    return respuesta_json


def extraer_texto(respuesta_json):
    try:
        return respuesta_json["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as error_dato:
        raise RuntimeError(f"La respuesta no trae el texto generado en el lugar esperado: {error_dato}")


def calcular_costo(respuesta_json, precio_entrada, precio_salida):
    try:
        uso = respuesta_json["usageMetadata"]
        tokens_entrada = uso["promptTokenCount"]
        tokens_salida = uso["candidatesTokenCount"]
    except KeyError as error_dato:
        raise RuntimeError(f"La respuesta no trae el conteo de tokens en el lugar esperado: {error_dato}")
    return (tokens_entrada * precio_entrada) + (tokens_salida * precio_salida)


def generar_respuesta(prompt):
    url, headers, body = armar_peticion(prompt)
    respuesta_json = enviar_peticion(url, headers, body)
    return extraer_texto(respuesta_json)


if __name__ == "__main__":
    try:
        print(generar_respuesta("Confirma que esta conexión vía API funciona correctamente, tu respuesta es la confirmación."))
    except (ValueError, RuntimeError) as error:
        print(f"No se pudo generar la respuesta: {error}")