import os
import requests
from dotenv import load_dotenv

load_dotenv()


def armar_peticion(prompt):
    api_key = os.getenv("API_KEY")
    modelo = "gemini-flash-latest"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    headers = {"x-goog-api-key": api_key}
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    return url, headers, body


def enviar_peticion(url, headers, body):
    respuesta = requests.post(url, headers=headers, json=body, timeout=60)
    return respuesta.json()


def extraer_texto(datos):
    return datos["candidates"][0]["content"]["parts"][0]["text"]


def generar_respuesta(prompt):
    url, headers, body = armar_peticion(prompt)
    datos = enviar_peticion(url, headers, body)
    return extraer_texto(datos)


print(generar_respuesta("Confirma en una frase corta que esta conexión funciona."))
