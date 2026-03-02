import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("CAPITAL_API_KEY")
API_USER = os.getenv("CAPITAL_API_USER")
API_PASS = os.getenv("CAPITAL_API_PASSWORD")
BASE_URL = "https://api-capital.backend-capital.com"

def login():
    url = f"{BASE_URL}/api/v1/session"
    payload = {"identifier": API_USER, "password": API_PASS}
    headers = {"X-CAP-API-KEY": API_KEY, "Content-Type": "application/json"}

    # debug opcional
    print("login payload:", payload, "headers:", headers)

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
    except requests.RequestException as exc:
        print("Error en login (excepción):", exc)
        return None, None

    if r.status_code != 200:
        print("Error en login:", r.status_code, r.text)
        return None, None

    cst = r.headers.get("CST")
    x_token = r.headers.get("X-SECURITY-TOKEN")
    return cst, x_token