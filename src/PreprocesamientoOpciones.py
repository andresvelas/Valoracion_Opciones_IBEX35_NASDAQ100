import pandas as pd
import numpy as np

class PreprocesamientoOpciones:
    def __init__(self, df_options, S0_dict):
        """
        Inicializa la clase con el DataFrame de opciones y precios subyacentes.
        
        df_options: DataFrame con columnas ['ticker', 'expiry', 'option_type', 'strike', 'bid', 'ask', 'lastPrice', 'impliedVolatility', 'volume', 'openInterest', 'lastTradeDate']
        S0_dict: diccionario {'TICKER': precio_actual, ...}
        """
        self.df_options = df_options.copy()
        self.S0_dict = S0_dict
        self.df_filtrado = None
        self.df_atm = None

    def convertir_fechas(self):
        """Convierte columnas de fechas a datetime."""
        self.df_options['expiry'] = pd.to_datetime(self.df_options['expiry'])
        self.df_options['lastTradeDate'] = pd.to_datetime(self.df_options['lastTradeDate'])
    
    def filtrar_vencimiento(self, semanas_objetivo=[21, 52]):
        """
        Filtra opciones por vencimientos cercanos a las semanas indicadas.
        semanas_objetivo: lista de semanas [21, 52] por defecto
        """
        today = pd.Timestamp.today()
        fechas_cercanas = []

        for semanas in semanas_objetivo:
            target = today + pd.to_timedelta(semanas*7, unit='d')
            fechas_disponibles = self.df_options['expiry'].unique()
            fecha_cercana = fechas_disponibles[np.abs(fechas_disponibles - target).argmin()]
            fechas_cercanas.append(fecha_cercana)
        
        self.df_filtrado = self.df_options[self.df_options['expiry'].isin(fechas_cercanas)]
        return self.df_filtrado

    def separar_call_put(self):
        """Separa CALL y PUT y unifica mayúsculas."""
        self.df_filtrado['option_type'] = self.df_filtrado['option_type'].str.upper()
        self.df_call = self.df_filtrado[self.df_filtrado['option_type'] == 'CALL']
        self.df_put = self.df_filtrado[self.df_filtrado['option_type'] == 'PUT']
        return self.df_call, self.df_put

    def seleccionar_atm(self):
        """Selecciona la opción ATM (strike más cercano a S0) por ticker."""
        df_atm = pd.DataFrame()

        for ticker in self.df_filtrado['ticker'].unique():
            S0 = self.S0_dict.get(ticker, np.nan)
            if np.isnan(S0):
                continue
            
            ticker_group = self.df_filtrado[self.df_filtrado['ticker'] == ticker].copy()
            ticker_group['atm_diff'] = abs(ticker_group['strike'] - S0)
            atm_row = ticker_group.loc[ticker_group['atm_diff'].idxmin()]
            df_atm = pd.concat([df_atm, atm_row.to_frame().T])
        
        self.df_atm = df_atm
        return self.df_atm

    def calcular_precio_mercado(self):
        """Calcula precio de mercado P_mkt usando mid-price o lastPrice si bid/ask inválidos."""
        if self.df_atm is None:
            raise ValueError("Primero debes ejecutar seleccionar_atm()")
        
        def mid_price(row):
            if row['bid'] > 0 and row['ask'] > 0:
                return (row['bid'] + row['ask']) / 2
            else:
                return row['lastPrice']
        
        self.df_atm['P_mkt'] = self.df_atm.apply(mid_price, axis=1)
        return self.df_atm

    def filtrar_liquidez(self, volumen_min=0, open_interest_min=100):
        """Filtra opciones con liquidez suficiente y lastTradeDate reciente."""
        if self.df_atm is None:
            raise ValueError("Primero debes ejecutar seleccionar_atm() y calcular_precio_mercado()")
        # Convertir lastTradeDate a datetime (si no lo es)
        self.df_atm['lastTradeDate'] = pd.to_datetime(
            self.df_atm['lastTradeDate'], errors='coerce'
        )

        # Eliminar filas donde lastTradeDate no se pudo convertir
        self.df_atm = self.df_atm.dropna(subset=['lastTradeDate'])

        # Ahora sí podemos comparar con today
        today = pd.Timestamp.today().tz_localize(None)
        self.df_atm['lastTradeDate'] = self.df_atm['lastTradeDate'].dt.tz_localize(None)

        self.df_atm = self.df_atm[
            (self.df_atm['volume'] > volumen_min) &
            (self.df_atm['openInterest'] > open_interest_min) 
        ]

        return self.df_atm

    def limpiar_nans(self):
        """Elimina opciones sin precio de mercado o strike/impliedVolatility faltantes."""
        self.df_atm = self.df_atm.dropna(subset=['P_mkt', 'strike', 'impliedVolatility'])
        return self.df_atm

    def resumen(self):
        """Resumen rápido del dataset ATM filtrado y limpio."""
        if self.df_atm is None:
            return None
        return {
            "num_opciones": len(self.df_atm),
            "tickers": self.df_atm['ticker'].unique(),
            "fechas_expiry": self.df_atm['expiry'].unique()
        }
