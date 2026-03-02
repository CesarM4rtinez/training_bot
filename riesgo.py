def calcular_riesgo(df, i=-1, riesgo_pct=0.01, recompensa_pct=0.02):
    """Calcula stop loss y take profit ofrecidos por la estrategia.

    - `riesgo_pct` es la fracción debajo de zona soporte/EMA usada para el SL.
    - `recompensa_pct` se aplica al precio de entrada para TP.
    """
    precio = df['close'].iloc[i]
    ema55 = df['EMA_55'].iloc[i]
    stop_loss = min(ema55, df['low'].iloc[i]) * (1 - riesgo_pct)
    take_profit = precio * (1 + recompensa_pct)
    return stop_loss, take_profit


def calcular_tamano_posicion(balance, precio, stop_loss, riesgo_pct=0.01):
    """Devuelve el tamaño de la posición en unidades de contrato a abrir.

    Se arriesga `riesgo_pct` del `balance`. Si la distancia entre
    precio y stop_loss es cero o muy pequeña, devuelve 1 como mínimo.
    """
    if balance is None or balance <= 0:
        return 1
    riesgo_dolares = balance * riesgo_pct
    distancia = abs(precio - stop_loss)
    if distancia <= 0:
        return 1
    size = riesgo_dolares / distancia
    return max(1, size)


def actualizar_trailing_stop(df, posicion, trailing_pct=0.01):
    precio_actual = df['close'].iloc[-1]
    if precio_actual > posicion['max_price']:
        posicion['max_price'] = precio_actual
        nuevo_stop = precio_actual * (1 - trailing_pct)
        if nuevo_stop > posicion['stop_loss']:
            posicion['stop_loss'] = nuevo_stop
            print(f">> Trailing Stop actualizado a {posicion['stop_loss']}")
    return posicion
