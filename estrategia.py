import ta
import pandas as pd

class EstrategiaTrading:
    def __init__(self, df, adx_threshold: float = 23.0):
        self.df = df
        # medias móviles y ADX tradicional
        self.df['EMA_10'] = ta.trend.EMAIndicator(df['close'], window=10).ema_indicator()
        self.df['EMA_55'] = ta.trend.EMAIndicator(df['close'], window=55).ema_indicator()
        self.df['ADX'] = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=14).adx()
        macd = ta.trend.MACD(df['close'])
        self.df['squeeze'] = macd.macd_diff()
        self.adx_threshold = adx_threshold

    def señal_entrada(self, i=-1):
        # 1. precio por encima de EMA55
        cond_tendencia = self.df['close'].iloc[i] > self.df['EMA_55'].iloc[i]
        # 2. squeeze pasa de rojo a verde
        cond_direccionalidad = self.df['squeeze'].iloc[i] > 0 and self.df['squeeze'].iloc[i-1] < 0
        # 3. ADX sobre el umbral que indica fuerza
        cond_fuerza = self.df['ADX'].iloc[i] > self.adx_threshold
        # 4. rebote sobre EMA (o al menos tocarla)
        cond_rebote = self.df['close'].iloc[i] >= self.df['EMA_55'].iloc[i]
        return cond_tendencia and cond_direccionalidad and cond_fuerza and cond_rebote

    def señal_salida(self, i=-1):
        # valle verde del squeeze gira rojo
        cond_debilidad = self.df['squeeze'].iloc[i] < 0 and self.df['squeeze'].iloc[i-1] > 0
        # ADX baja del umbral
        cond_perdida_fuerza = self.df['ADX'].iloc[i] < self.adx_threshold
        return cond_debilidad or cond_perdida_fuerza
