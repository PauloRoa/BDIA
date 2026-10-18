import os
import requests
from dotenv import load_dotenv

load_dotenv()

MODELO = "gemini-flash-latest"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent"


def generar_respuesta(prompt):
    api_key = os.getenv("API_KEY")
    headers = {"x-goog-api-key": api_key}
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    respuesta = requests.post(URL, headers=headers, json=body, timeout=60)
    datos = respuesta.json()
    return datos["candidates"][0]["content"]["parts"][0]["text"]


print(generar_respuesta("Confirma en una frase corta que esta conexión funciona."))