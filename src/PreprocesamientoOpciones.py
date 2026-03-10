import pandas as pd
import numpy as np

class PreprocesamientoOpciones:
    def __init__(self, df_options, S0_dict):
        self.df_options = df_options.copy()
        self.S0_dict = S0_dict
        self.df_filtrado = None
        self.df_atm = None
        self.df_call = None
        self.df_put = None

    def convertir_fechas(self):
        self.df_options['expiry'] = pd.to_datetime(self.df_options['expiry'])
        self.df_options['lastTradeDate'] = pd.to_datetime(self.df_options['lastTradeDate']).dt.tz_localize(None)
        return self

    def filtrar_vencimiento(self, semanas_objetivo=[21, 52]):
        # Usamos la fecha máxima del dataset como 'hoy' para consistencia histórica
        today = self.df_options['lastTradeDate'].max()
        fechas_disponibles = self.df_options['expiry'].unique()
        fechas_cercanas = []

        for semanas in semanas_objetivo:
            target = today + pd.to_timedelta(semanas*7, unit='d')
            fecha_cercana = fechas_disponibles[np.abs(fechas_disponibles - target).argmin()]
            fechas_cercanas.append(fecha_cercana)
        
        self.df_filtrado = self.df_options[self.df_options['expiry'].isin(fechas_cercanas)].copy()
        return self

    def separar_call_put(self):
        if self.df_filtrado is None: return self
        self.df_filtrado['option_type'] = self.df_filtrado['option_type'].str.upper()
        self.df_call = self.df_filtrado[self.df_filtrado['option_type'] == 'CALL'].copy()
        self.df_put = self.df_filtrado[self.df_filtrado['option_type'] == 'PUT'].copy()
        return self

    def seleccionar_atm(self):
        lista_atm = []
        for ticker in self.df_filtrado['ticker'].unique():
            S0 = self.S0_dict.get(ticker)
            if S0 is None or np.isnan(S0): continue
            
            # Buscamos ATM por cada combinación de Ticker y Expiración
            for expiry in self.df_filtrado['expiry'].unique():
                grupo = self.df_filtrado[(self.df_filtrado['ticker'] == ticker) & 
                                         (self.df_filtrado['expiry'] == expiry)].copy()
                if not grupo.empty:
                    grupo['atm_diff'] = abs(grupo['strike'] - S0)
                    atm_row = grupo.loc[grupo['atm_diff'].idxmin()]
                    lista_atm.append(atm_row)
        
        self.df_atm = pd.DataFrame(lista_atm) if lista_atm else pd.DataFrame()
        return self

    def calcular_precio_mercado(self):
        if self.df_atm.empty: return self
        # Vectorizado para evitar el error de DataFrame sin columnas
        self.df_atm['P_mkt'] = np.where(
            (self.df_atm['bid'] > 0) & (self.df_atm['ask'] > 0),
            (self.df_atm['bid'] + self.df_atm['ask']) / 2,
            self.df_atm['lastPrice']
        )
        return self

    def filtrar_liquidez(self, volumen_min=0, open_interest_min=10):
        if self.df_atm.empty: return self
        
        # Filtro de seguridad
        condicion = (self.df_atm['volume'] >= volumen_min) & \
                    (self.df_atm['openInterest'] >= open_interest_min)
        
        self.df_atm = self.df_atm[condicion].copy()
        return self

    def limpiar_nans(self):
        if self.df_atm.empty: return self
        cols_necesarias = ['P_mkt', 'strike', 'impliedVolatility']
        self.df_atm = self.df_atm.dropna(subset=cols_necesarias).copy()
        return self

    def ejecutar_pipeline(self, semanas=[21, 52], oi_min=10):
        """Ejecuta todos los pasos de forma secuencial."""
        print("Iniciando Pipeline de Opciones...")
        self.convertir_fechas()
        self.filtrar_vencimiento(semanas)
        self.separar_call_put()
        self.seleccionar_atm()
        
        if self.df_atm.empty:
            print("No se encontraron opciones que coincidan con los S0 proporcionados.")
            return self.df_atm
            
        self.calcular_precio_mercado()
        self.filtrar_liquidez(open_interest_min=oi_min)
        self.limpiar_nans()
        
        print(f"✅ Pipeline finalizado. {len(self.df_atm)} contratos listos.")
        return self.df_atm

    def resumen(self):
        if self.df_atm is None or self.df_atm.empty:
            return "No hay datos procesados."
        return {
            "num_opciones": len(self.df_atm),
            "tickers": self.df_atm['ticker'].unique().tolist(),
            "vencimientos": [d.strftime('%Y-%m-%d') for d in self.df_atm['expiry'].unique()]
        }