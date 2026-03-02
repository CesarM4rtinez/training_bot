# 🤖 Bot de Trading Automático - Capital.com

Sistema automático de trading basado en la **estrategia de Jaime Merino (TradingLatino)** usando Python, Pandas, TA-Lib y la API de Capital.com.

---

## 📋 Requisitos Previos

- Python 3.7+
- Cuenta en [Capital.com](https://capital.com) (probado con "Analista l")
- API credentials configuradas en `.env`

---

## 🔧 Configuración Inicial

### 1. Variables de Entorno (`.env`)

```dotenv
CAPITAL_API_USER=tu_email@gmail.com
CAPITAL_API_PASSWORD=tu_contraseña
CAPITAL_API_KEY=tu_api_key
```

**Importante**: Sin comentarios al final de las líneas.

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

O manualmente:
```bash
pip install requests pandas ta python-dotenv
```

### 3. Crear Virtual Environment (Opcional pero Recomendado)

```bash
python -m venv bot
.\bot\Scripts\activate
pip install -r requirements.txt
```

---

## ▶️ Cómo Ejecutar

### Opción 1: Bot por Defecto (BTCUSD)
```bash
python main.py
```

### Opción 2: Múltiples Activos
```bash
python main.py BTCUSD ETHUSD GOLD GOLD
```

### Opción 3: Un Activo Específico
```bash
python main.py ETHUSD
```

---

## 📊 Estrategia de Trading

Se basa en **4 indicadores clave**:

### Indicadores
- **EMA 10** y **EMA 55**: Zonas de soporte/resistencia
- **ADX (14)**: Mide la fuerza de la tendencia (umbral = 23)
- **Squeeze Momentum**: Indica oportunidades (rojo/verde)

### Reglas de ENTRADA (Long/Compra)

1. **Tendencia**: Precio > EMA 55
2. **Direccionalidad**: Squeeze pasa de rojo → verde
3. **Fuerza**: ADX > 23
4. **Gatillo**: Precio toca/rebota en EMA 55

### Reglas de SALIDA (Cierre)

1. **Debilidad**: Squeeze pasa de verde → rojo
2. **Pérdida de fuerza**: ADX < 23
3. **Stop Loss**: Siempre bajo el mínimo anterior o EMA 55
4. **Take Profit**: +2% sobre el precio de entrada (configurable)

---

## 💰 Gestión de Riesgo y Capital

### Tamaño de Posición

```
size = (saldo × riesgo_pct) / (entrada - stop_loss)
```

**Ejemplo**:
- Saldo: $1,500
- Riesgo: 1% = $15
- Entrada: $65,000
- Stop Loss: $64,500
- **Size = 15 / 500 = 0.03 BTC**

### Parámetros Configurables

En `main.py`:
```python
run_bot(
    epics=["BTCUSD", "ETHUSD"],  # activos a tradear
    riesgo_pct=0.01,              # 1% de riesgo (0.01)
    account_name="Analista l"     # tu cuenta
)
```

---

## 📍 Estructura de Archivos

```
training_bot/
├── main.py              # Loop principal del bot
├── auth.py              # Autenticación con Capital.com
├── broker.py            # Funciones de conexión API
├── estrategia.py        # Lógica de indicadores y señales
├── riesgo.py            # Cálculo de tamaño y gestión de capital
├── requirements.txt     # Dependencias Python
├── .env                 # Credenciales (NO COMMITAR!)
└── README_BOT.md        # Este archivo
```

---

## 📈 Ejemplo de Ejecución

```
sesion iniciada | cuenta: Analista l | activos: BTCUSD, ETHUSD

=== nueva iteración ===
saldo: $1.49 | riesgo por operación: 1%
BTCUSD: recibidos 100 precios
>> BTCUSD: señal de ENTRADA
  talla=1 | entrada=$65234.50 | SL=$64800.00 | TP=$66539.00
  posición abierta: abc123xyz

ETHUSD: recibidos 100 precios
posiciones activas: 1 | epics: BTCUSD

sin posiciones abiertas
```

---

## ⚙️ Funciones Principales

### `run_bot(epics, riesgo_pct, account_name)`
Inicia el loop principal del trading.

### `get_prices(epic, cst, x_token)`
Obtiene últimas 100 velas de 1 minuto.

### `place_order(epic, direction, size, stop_loss, take_profit, cst, x_token)`
Abre una posición en el mercado.

### `close_position(deal_id, cst, x_token)`
Cierra una posición abierta por su ID.

### `get_account_balance(cst, x_token, account_name)`
Consulta el saldo disponible de la cuenta.

### `calcular_tamano_posicion(balance, precio, stop_loss, riesgo_pct)`
Calcula el tamaño de lote según riesgo.

### `actualizar_trailing_stop(df, posicion, trailing_pct)`
Ajusta el stop-loss automáticamente al alza (1% por defecto).

---

## 🚨 Troubleshooting

### `saldo disponible: None`
- Verifica que `account_name` coincida exactamente con tu cuenta en Capital.com
- Comprueba credenciales en `.env`
- Ejecuta: `python -c "from broker import *; from auth import *; print(get_account_balance(login()[0], login()[1], 'Analista l'))"`

### `Error abriendo posición`
- Verifica que el saldo sea suficiente
- Comprueba que el epic sea válido
- Revisa límites de la cuenta (máx. posiciones, tamaño)

### Bot se queda "congelado"
- El bot ejecuta una iteración cada 60 segundos por defecto
- Usa Ctrl+C para detener
- Revisa los logs en consola

---

## 📝 Notas Importantes

1. **NO USAR EN PRODUCCIÓN** sin backtesting exhaustivo
2. Asegurate de entender la estrategia antes de usarla
3. Comienza con simulación o capital pequeño
4. Los indicadores tienen retrasos, lo que puede afectar ejecución
5. Capital.com cobra comisiones y spreads

---

## 📞 Soporte

Para problemas específicos, verifica:
1. Logs de la terminal
2. Respuestas HTTP de la API en `broker.py`
3. Estado de la cuenta en Capital.com

---

**Última actualización**: 1 de marzo de 2026
**Estrategia**: Jaime Merino - TradingLatino (Día 1)
**Plataforma**: Capital.com CFD Trading
