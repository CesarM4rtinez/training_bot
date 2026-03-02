import time
import os
import json
from datetime import datetime
import pandas as pd
from broker import get_prices, place_order, close_position, get_account_balance
from estrategia import EstrategiaTrading
from riesgo import calcular_riesgo, calcular_tamano_posicion, actualizar_trailing_stop
from auth import login

def run_bot(epics=None, riesgo_pct=0.01, account_name="Analista l"):
    """Arranca el bot en uno o varios símbolos paramétricos.

    - `epics` puede ser una cadena ("BTCUSD") o una lista de epics. El valor
      por defecto es ["BTCUSD"].
    - `riesgo_pct` es la fracción del saldo que se arriesgará en cada operación.
    - `account_name` es un campo informativo (tu cuenta "Analista l").
    """
    if epics is None:
        epics = ["BTCUSD"]
    elif isinstance(epics, str):
        epics = [epics]

    # 🔑 Login y tokens de sesión
    cst, x_token = login()
    if not cst or not x_token:
        print("No se pudo iniciar sesión")
        return
    print(f"sesion iniciada | cuenta: {account_name} | activos: {', '.join(epics)}")

    posiciones = {}  # mapa epic -> dict de posición

    while True:
        print("\n=== nueva iteración ===")
        balance = get_account_balance(cst=cst, x_token=x_token, account_name=account_name)
        if balance is None:
            print("No se pudo consultar el saldo, abortando iteración")
            time.sleep(60)
            continue
        print(f"saldo: ${balance:.2f} | riesgo por operación: {riesgo_pct*100}%")

        for epic in epics:
            data = get_prices(epic, cst=cst, x_token=x_token)
            if not data or "prices" not in data:
                print(f"{epic}: no se recibieron precios válidos", data)
                continue

            df = pd.DataFrame(data['prices'])

            def _mid(p):
                if p is None:
                    return None
                if isinstance(p, dict):
                    if "mid" in p:
                        return p["mid"]
                    ask = p.get("ask")
                    bid = p.get("bid")
                    if ask is not None and bid is not None:
                        return (ask + bid) / 2
                return None

            df['close'] = df['closePrice'].apply(_mid)
            df['open']  = df['openPrice'].apply(_mid)
            df['high']  = df['highPrice'].apply(_mid)
            df['low']   = df['lowPrice'].apply(_mid)
            df['volume']= df['lastTradedVolume']

            if df[['close', 'open', 'high', 'low']].isna().any().any():
                print(f"{epic}: precios con valores nulos, saltando")
                continue

            estrategia = EstrategiaTrading(df)

            # gestionar posición existente: trailing stop y chequeo SL/TP
            if epic in posiciones:
                pos = posiciones[epic]
                precio_act = df['close'].iloc[-1]
                ganancia_pct = ((precio_act - pos['entry_price']) / pos['entry_price']) * 100
                
                # actualizar trailing stop
                pos = actualizar_trailing_stop(df, pos)
                
                # verificar SL/TP
                if precio_act <= pos['stop_loss']:
                    print(f"{epic}: cierre por STOP LOSS en ${precio_act:.2f}")
                    close_position(pos['id'], cst=cst, x_token=x_token)
                    posiciones.pop(epic, None)
                    continue
                if precio_act >= pos['take_profit']:
                    print(f"{epic}: cierre por TAKE PROFIT en ${precio_act:.2f} | ganancia {ganancia_pct:.2f}%")
                    close_position(pos['id'], cst=cst, x_token=x_token)
                    posiciones.pop(epic, None)
                    continue

            # señal de entrada
            if estrategia.señal_entrada() and epic not in posiciones:
                print(f">> {epic}: señal de ENTRADA")
                stop, tp = calcular_riesgo(df)
                precio_entrada = df['close'].iloc[-1]
                size = int(calcular_tamano_posicion(balance, precio_entrada, stop, riesgo_pct))
                print(f"  talla={size} | entrada=${precio_entrada:.2f} | SL=${stop:.2f} | TP=${tp:.2f}")
                respuesta = place_order(
                    epic, "BUY", size=size,
                    stop_loss=stop, take_profit=tp,
                    cst=cst, x_token=x_token
                )
                deal = respuesta.get("dealId")
                if deal:
                    posiciones[epic] = {
                        "id": deal,
                        "entry_price": precio_entrada,
                        "stop_loss": stop,
                        "take_profit": tp,
                        "max_price": precio_entrada
                    }
                    print(f"  posición abierta: {deal}")
                else:
                    print(f"  ERROR: no se obtuvo dealId de la orden")

            # señal de salida
            if estrategia.señal_salida() and epic in posiciones:
                print(f">> {epic}: señal de SALIDA")
                pos = posiciones.pop(epic)
                close_position(pos['id'], cst=cst, x_token=x_token)

            # --- Generar informe técnico por epic para esta iteración ---
            try:
                os.makedirs('reports', exist_ok=True)
                report = {}
                report['timestamp_utc'] = datetime.utcnow().isoformat() + 'Z'
                report['epic'] = epic
                # timeframe: get_prices default is MINUTE; si cambia, pásalo explícito
                report['timeframe'] = 'MINUTE'
               