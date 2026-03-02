#!/usr/bin/env python3
"""
Script de diagnóstico para verificar que el bot está configurado correctamente.
Ejecuta: python test_bot.py
"""

import sys
from auth import login
from broker import get_prices, get_account_balance, place_order, close_position
from estrategia import EstrategiaTrading
from riesgo import calcular_riesgo, calcular_tamano_posicion

print("=" * 60)
print("🔍 DIAGNÓSTICO DEL BOT DE TRADING")
print("=" * 60)

# Test 1: Login
print("\n1️⃣ Verificando autenticación...")
cst, x_token = login()
if cst and x_token:
    print("   ✅ Login exitoso")
else:
    print("   ❌ Login fallido - verifica .env")
    sys.exit(1)

# Test 2: Obtener precios
print("\n2️⃣ Verificando obtención de precios...")
data = get_prices("GOLD", cst=cst, x_token=x_token)
if data and "prices" in data:
    num_precios = len(data["prices"])
    print(f"   ✅ Recibidos {num_precios} precios de GOLD")
else:
    print("   ❌ No se pudieron obtener precios")
    sys.exit(1)

# Test 3: Balance de cuenta
print("\n3️⃣ Verificando saldo...")
balance = get_account_balance(cst=cst, x_token=x_token, account_name="Analista l")
if balance is not None:
    print(f"   ✅ Saldo disponible: ${balance:.2f}")
else:
    print("   ❌ No se pudo consultar el saldo - verifica account_name")

# Test 4: Indicadores
print("\n4️⃣ Verificando indicadores...")
import pandas as pd
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

estrategia = EstrategiaTrading(df)
entrada = estrategia.señal_entrada()
salida = estrategia.señal_salida()

print(f"   ✅ Indicadores calculados")
print(f"      - EMA 10: {df['EMA_10'].iloc[-1]:.2f}")
print(f"      - EMA 55: {df['EMA_55'].iloc[-1]:.2f}")
print(f"      - ADX: {df['ADX'].iloc[-1]:.2f}")
print(f"      - Squeeze: {df['squeeze'].iloc[-1]:.4f}")
print(f"      - Señal ENTRADA: {entrada}")
print(f"      - Señal SALIDA: {salida}")

# Test 5: Cálculo de riesgo
print("\n5️⃣ Verificando gestión de capital...")
stop, tp = calcular_riesgo(df)
precio = df['close'].iloc[-1]
size = calcular_tamano_posicion(balance, precio, stop, 0.01)
print(f"   ✅ Cálculo de posición")
print(f"      - Entrada: ${precio:.2f}")
print(f"      - Stop Loss: ${stop:.2f}")
print(f"      - Take Profit: ${tp:.2f}")
print(f"      - Tamaño (1% riesgo): {size:.4f} unidades")

print("\n" + "=" * 60)
print("✨ BOT READY - Todos los sistemas operativos")
print("=" * 60)
print("\nEjecuta: python main.py BTCUSD")
print("O:       python main.py BTCUSD ETHUSD XAGSD")
