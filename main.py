import time
import os
import json
import glob
from datetime import datetime, timezone
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
        epics = ["GOLD"]
    elif isinstance(epics, str):
        epics = [epics]

    # 🔑 Login y tokens de sesión
    cst, x_token = login()
    if not cst or not x_token:
        print("No se pudo iniciar sesión")
        return
    print(f"Bot iniciado | cuenta: {account_name} | activos: {', '.join(epics)}")

    posiciones = {}  # mapa epic -> dict de posición

    while True:
        print("\n=== iteración ===")
        balance = get_account_balance(cst=cst, x_token=x_token, account_name=account_name)
        if balance is None:
            print("Error: no se pudo consultar el saldo")
            time.sleep(60)
            continue

        tabla_datos = []  # guardar datos técnicos de cada epic para mostrar al final

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
                    close_position(pos['id'], cst=cst, x_token=x_token)
                    print(f"[-] {epic}: operación cerrada por STOP LOSS")
                    posiciones.pop(epic, None)
                    continue
                if precio_act >= pos['take_profit']:
                    close_position(pos['id'], cst=cst, x_token=x_token)
                    print(f"[-] {epic}: operación cerrada por TAKE PROFIT")
                    posiciones.pop(epic, None)
                    continue

            # recopilar info antes de procesar entrada
            ema55_calc = df['EMA_55'].iloc[-1]
            precio_actual = df['close'].iloc[-1]
            
            # señal de entrada
            if estrategia.señal_entrada() and epic not in posiciones:
                stop, tp = calcular_riesgo(df)
                precio_entrada = df['close'].iloc[-1]
                size = int(calcular_tamano_posicion(balance, precio_entrada, stop, riesgo_pct))
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
                    print(f"[+] {epic}: COMPRA abierta a ${precio_entrada:.2f} | SL: ${stop:.2f} | TP: ${tp:.2f}")
            elif epic not in posiciones:
                # mostrar a qué precio se espera la entrada y con qué SL/TP
                stop_esperado, tp_esperado = calcular_riesgo(df)
                # detallar por qué aún no hay señal completa
                cond_tend = precio_actual > ema55_calc
                squeeze = df['squeeze'].iloc[-1]
                squeeze_prev = df['squeeze'].iloc[-2] if len(df) > 1 else 0
                cond_squeeze = squeeze > 0 and squeeze_prev < 0
                adx_val = df['ADX'].iloc[-1]
                cond_adx = adx_val > estrategia.adx_threshold
                cond_rebote = precio_actual >= ema55_calc
                motivos = []
                if not cond_tend:
                    motivos.append('precio < EMA55')
                if not cond_squeeze:
                    motivos.append('squeeze no cruzó a verde')
                if not cond_adx:
                    motivos.append(f'ADX {adx_val:.2f} < {estrategia.adx_threshold}')
                if not cond_rebote:
                    motivos.append('no hay rebote sobre EMA55')
                motivo_text = ', '.join(motivos) if motivos else 'condiciones cumplidas'
                print(f"[~] {epic}: esperando COMPRA en ${ema55_calc:.2f} (actual: ${precio_actual:.2f}) | SL: ${stop_esperado:.2f} | TP: ${tp_esperado:.2f} -- {motivo_text}")

            # señal de salida
            if estrategia.señal_salida() and epic in posiciones:
                pos = posiciones.pop(epic)
                close_position(pos['id'], cst=cst, x_token=x_token)
                print(f"[-] {epic}: operación cerrada por SEÑAL DE SALIDA")

            # recopilar datos técnicos para tabla
            ema10 = df['EMA_10'].iloc[-1]
            ema55 = df['EMA_55'].iloc[-1]
            adx = df['ADX'].iloc[-1]
            squeeze = df['squeeze'].iloc[-1]
            precio = df['close'].iloc[-1]
            tabla_datos.append({
                'epic': epic,
                'ema10': f"{ema10:.2f}",
                'ema55': f"{ema55:.2f}",
                'adx': f"{adx:.2f}",
                'squeeze': f"{squeeze:.4f}",
                'precio': f"{precio:.2f}"
            })

            # --- Generar informe técnico por epic para esta iteración ---
            try:
                os.makedirs('reports', exist_ok=True)
                report = {}
                report['timestamp_utc'] = datetime.now(timezone.utc).isoformat() + 'Z'
                report['epic'] = epic
                # timeframe: get_prices default is MINUTE; si cambia, pásalo explícito
                report['timeframe'] = 'MINUTE'
                report['num_prices'] = len(data.get('prices', []))
                # snapshot times si existen
                try:
                    report['first_snapshot'] = df['snapshotTimeUTC'].iloc[0]
                    report['last_snapshot'] = df['snapshotTimeUTC'].iloc[-1]
                except Exception:
                    report['first_snapshot'] = None
                    report['last_snapshot'] = None

                # indicadores y último precio
                report['indicators'] = {
                    'EMA_10': float(df['EMA_10'].iloc[-1]),
                    'EMA_55': float(df['EMA_55'].iloc[-1]),
                    'ADX': float(df['ADX'].iloc[-1]),
                    'squeeze': float(df['squeeze'].iloc[-1])
                }
                report['last_price'] = float(df['close'].iloc[-1])
                report['open_last'] = float(df['open'].iloc[-1])
                report['high_last'] = float(df['high'].iloc[-1])
                report['low_last'] = float(df['low'].iloc[-1])
                report['volume_last'] = int(df['volume'].iloc[-1]) if 'volume' in df.columns else None

                # señales
                report['signal_entry'] = bool(estrategia.señal_entrada())
                report['signal_exit'] = bool(estrategia.señal_salida())

                # posición y cálculo de riesgo/size si hubiera entrada
                if report['signal_entry'] and epic not in posiciones:
                    stop, tp = calcular_riesgo(df)
                    precio_entrada = df['close'].iloc[-1]
                    size = int(calcular_tamano_posicion(balance, precio_entrada, stop, riesgo_pct))
                    report['planned_order'] = {
                        'entry_price': float(precio_entrada),
                        'stop_loss': float(stop),
                        'take_profit': float(tp),
                        'size': size,
                        'risk_pct': float(riesgo_pct)
                    }
                else:
                    report['planned_order'] = None

                # info de posición actual si existe
                if epic in posiciones:
                    pos = posiciones[epic]
                    report['position'] = {
                        'id': pos.get('id'),
                        'entry_price': pos.get('entry_price'),
                        'stop_loss': pos.get('stop_loss'),
                        'take_profit': pos.get('take_profit'),
                        'max_price': pos.get('max_price')
                    }
                else:
                    report['position'] = None

                # balance
                report['account_balance'] = float(balance)

                # guardar reporte con timestamp para backlog
                fname_timestamped = f"reports/report_{epic}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.json"
                with open(fname_timestamped, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                
                # también guardar como 'latest' para acceso rápido
                fname_latest = f"reports/report_{epic}_latest.json"
                with open(fname_latest, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                
                # rotación: eliminar reportes antiguos, mantener máximo 3 por epic
                try:
                    import glob
                    pattern = f"reports/report_{epic}_*.json"
                    reports = sorted(glob.glob(pattern), reverse=True)
                    # no contar el _latest.json en la rotación; eliminar timestamped viejos
                    timestamped = [f for f in reports if '_latest.json' not in f]
                    if len(timestamped) > 3:
                        para_eliminar = timestamped[3:]  # mantener max 3 históricos
                        for old_file in para_eliminar:
                            try:
                                os.remove(old_file)
                            except:
                                pass  # ignorar errores al borrar
                except:
                    pass  # ignorar errores en rotación
                
            except Exception as e:
                print(f"Error en informe {epic}: {e}")

        # mostrar tabla técnica resumida
        if tabla_datos:
            print("\n{:<12} {:<10} {:<10} {:<8} {:<10} {:<12}".format("EPIC", "EMA_10", "EMA_55", "ADX", "SQUEEZE", "PRECIO"))
            print("-" * 70)
            for row in tabla_datos:
                print("{:<12} {:<10} {:<10} {:<8} {:<10} {:<12}".format(
                    row['epic'], row['ema10'], row['ema55'], row['adx'], row['squeeze'], row['precio']
                ))

        # mostrar estado de posiciones
        if posiciones:
            print(f"\n[>] Posiciones activas: {len(posiciones)}")
            for epic, pos in posiciones.items():
                print(f"    {epic}: entrada ${pos['entry_price']:.2f} | SL ${pos['stop_loss']:.2f} | TP ${pos['take_profit']:.2f}")
        else:
            print("\n[o] Sin operaciones abiertas")
        
        time.sleep(60)

if __name__ == "__main__":
    import sys
    # aceptar epics como argumentos, por ejemplo: python main.py BTCUSD ETHUSD
    args = sys.argv[1:]
    if args:
        run_bot(epics=args)
    else:
        run_bot()  # usa valor por defecto