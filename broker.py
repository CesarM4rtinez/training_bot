import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("CAPITAL_API_KEY")
BASE_URL = "https://api-capital.backend-capital.com"

headers = {
    "X-CAP-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

def place_order(epic, direction="BUY", size=1, stop_loss=None, take_profit=None, cst=None, x_token=None):
    """Abre una nueva posición.
    Opcionalmente se pueden pasar tokens de sesión para hacer la llamada
    desde un entorno ya logueado (cst/x_token)."""
    url = f"{BASE_URL}/api/v1/positions"
    payload = {
        "epic": epic,
        "direction": direction,
        "size": size,
        "orderType": "MARKET"
    }
    if stop_loss:
        payload["stopLevel"] = stop_loss
    if take_profit:
        payload["limitLevel"] = take_profit

    hdr = headers.copy()
    if cst:
        hdr["CST"] = cst
    if x_token:
        hdr["X-SECURITY-TOKEN"] = x_token

    try:
        r = requests.post(url, headers=hdr, json=payload)
        if r.status_code != 200:
            print(f"Error abriendo posición {epic}:", r.status_code, r.text)
            return {}
        return r.json()
    except Exception as e:
        print(f"Excepción al abrir posición {epic}:", e)
        return {}


def close_position(deal_id, cst=None, x_token=None):
    """Cierra una posición abierta usando su dealId."""
    url = f"{BASE_URL}/api/v1/positions/{deal_id}"
    hdr = headers.copy()
    if cst:
        hdr["CST"] = cst
    if x_token:
        hdr["X-SECURITY-TOKEN"] = x_token
    try:
        r = requests.delete(url, headers=hdr)
        if r.status_code != 200:
            print(f"Error cerrando posición {deal_id}:", r.status_code, r.text)
            return {}
        return r.json()
    except Exception as e:
        print(f"Excepción al cerrar posición {deal_id}:", e)
        return {}


def get_account_balance(cst=None, x_token=None, account_name=None):
    """Consulta el saldo de la cuenta.
    
    Devuelve el `available` si está disponible, en caso contrario `balance`.
    Si se pasa `account_name` se intenta devolver únicamente de esa cuenta;
    de lo contrario se elige la cuenta marcada como "preferred" o la primera.
    """
    url = f"{BASE_URL}/api/v1/accounts"
    hdr = headers.copy()
    if cst:
        hdr["CST"] = cst
    if x_token:
        hdr["X-SECURITY-TOKEN"] = x_token
    r = requests.get(url, headers=hdr)
    if r.status_code != 200:
        print("Error consultando balance:", r.status_code, r.text)
        return None
    try:
        data = r.json()
    except ValueError:
        print("Balance: respuesta no JSON")
        return None

    # respuesta esperada:
    # {"accounts":[{...balance":{"balance":7.35,"available":1.49},...} ]}
    if isinstance(data, dict) and "accounts" in data and isinstance(data["accounts"], list):
        # buscar cuenta por nombre si se pide
        chosen = None
        if account_name:
            for acct in data["accounts"]:
                if acct.get("accountName") == account_name:
                    chosen = acct
                    break
        # si no se eligió aún, tratar de preferida
        if chosen is None:
            for acct in data["accounts"]:
                if acct.get("preferred"):
                    chosen = acct
                    break
        # por último, primera de la lista
        if chosen is None and data["accounts"]:
            chosen = data["accounts"][0]
        if chosen:
            bal = chosen.get("balance", {})
            # prefer available
            if isinstance(bal, dict):
                return bal.get("available") or bal.get("balance")
            return bal
    # casos triviales: lista plana
    if isinstance(data, list) and data:
        item = data[0]
        if isinstance(item, dict):
            for key in ("equity", "balance", "cash", "available"):
                if key in item:
                    return item[key]
    # búsqueda directa en dict
    if isinstance(data, dict):
        for key in ("equity", "balance", "cash", "available"):
            if key in data:
                return data[key]
    return None

def get_prices(epic="ETHUSD", resolution="MINUTE", num_points=100, cst=None, x_token=None):
    url = f"{BASE_URL}/api/v1/prices/{epic}?resolution={resolution}&max={num_points}"
    headers = {
        "X-CAP-API-KEY": API_KEY,
        "CST": cst,
        "X-SECURITY-TOKEN": x_token,
        "Content-Type": "application/json"
    }
    r = requests.get(url, headers=headers)
    return r.json()
