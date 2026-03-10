import pandas as pd
import numpy as np
import yfinance as yf

class PreprocesamientoActivos:
    def __init__(self, df_hist):
        """
        Inicializa la clase con el DataFrame histórico.
        df_hist: DataFrame con MultiIndex en columnas (Price, Ticker) y fechas como índice.
        """
        self.df_hist = df_hist.copy()
        self.df_filtrado = None
        self.adj_close = None
        self.S0 = None
        self.log_returns = None
        self.sigma_daily = None
        self.sigma_annual = None

    def filtrar_fecha(self, fecha_valoracion):
        """Mantener solo datos hasta la fecha de valoración."""
        fecha_valoracion = pd.Timestamp(fecha_valoracion)
        self.df_filtrado = self.df_hist.loc[self.df_hist.index <= fecha_valoracion]
        return self.df_filtrado

    def seleccionar_adj_close(self):
        """Seleccionar columna Adj Close y calcular precio inicial S0 por activo."""
        if self.df_filtrado is None:
            raise ValueError("Primero debes ejecutar filtrar_fecha()")
        
        # Seleccionar Adj Close 
        self.adj_close = self.df_filtrado["Adj Close"]
        
        # Precio inicial S0: último precio disponible por activo
        self.S0 = self.adj_close.iloc[-1]
        return self.adj_close, self.S0

    def calcular_retornos_log(self, window=100, min_obs=30):
        """
        Calcular retornos logarítmicos usando los últimos 'window' precios disponibles.
        min_obs: número mínimo de precios necesarios para estimar retornos.
        """
        if self.adj_close is None:
            raise ValueError("Primero debes ejecutar seleccionar_adj_close()")
        
        log_returns = pd.DataFrame(index=self.adj_close.index)
        valid_assets = []

        for ticker in self.adj_close.columns:
            prices = self.adj_close[ticker].dropna()
            if len(prices) < min_obs:
                print(f"⚠️ Ticker {ticker} tiene menos de {min_obs} precios.")
                continue
            
            # Tomar los últimos 'window' precios disponibles
            prices_window = prices.tail(window)
            r = np.log(prices_window / prices_window.shift(1)).dropna()
            log_returns[ticker] = r
            valid_assets.append(ticker)
        
        self.log_returns = log_returns
        return self.log_returns

    def estimar_volatilidad(self, anualizar=True, dias_mercado=252):
        """
        Estimar volatilidad histórica diaria y anualizada.
        """
        if self.log_returns is None:
            raise ValueError("Primero debes ejecutar calcular_retornos_log()")
        
        self.sigma_daily = self.log_returns.std()
        if anualizar:
            self.sigma_annual = self.sigma_daily * np.sqrt(dias_mercado)
            return self.sigma_daily, self.sigma_annual
        else:
            self.sigma_annual = None
            return self.sigma_daily, None


    def asignar_volatilidad_proxy(self, sigma_dict, min_obs=30, metodo="promedio"):
        """
        Asigna volatilidad proxy a tickers con menos de 'min_obs' precios.
        
        sigma_dict: dict o pd.Series con la volatilidad anual de cada ticker calculada hasta ahora.
        min_obs: número mínimo de precios necesarios para que un ticker sea válido.
        metodo: 'promedio', 'mediana', 'max', 'min'.
        
        Devuelve un diccionario con la volatilidad completa (original + proxy).
        """
        sigma_proxy = sigma_dict.copy()
        
        for ticker in self.adj_close.columns:
            n_precios = len(self.adj_close[ticker])
            if n_precios < min_obs:
                print(f"⚠️ Ticker {ticker} tiene {n_precios} precios (<{min_obs}). Se asignará volatilidad proxy.")
                
                # Elegir los tickers válidos para calcular proxy
                tickers_validos = [t for t in sigma_dict.index if t != ticker and sigma_dict[t] is not None]
                if len(tickers_validos) == 0:
                    print(f"⚠️ No hay tickers válidos para asignar proxy a {ticker}. Se asigna NaN")
                    sigma_proxy[ticker] = np.nan
                    continue
                
                if metodo == "promedio":
                    sigma_proxy[ticker] = sigma_dict[tickers_validos].mean()
                elif metodo == "mediana":
                    sigma_proxy[ticker] = sigma_dict[tickers_validos].median()
                elif metodo == "max":
                    sigma_proxy[ticker] = sigma_dict[tickers_validos].max()
                elif metodo == "min":
                    sigma_proxy[ticker] = sigma_dict[tickers_validos].min()
                else:
                    raise ValueError(f"Método '{metodo}' no soportado. Usa: promedio, mediana, max, min")
                
                print(f"✅ {ticker} asignado volatilidad proxy ({metodo}): {sigma_proxy[ticker]:.4f}")
        
        return sigma_proxy
    def calcular_dividend_yield(self, dividends_csv="../data/dividends.csv"):
        """
        Calcula el dividend yield anualizado por ticker usando dividends.csv por defecto.
        
        Parámetros:
        -----------
        dividends_csv : str, opcional
            Ruta al archivo CSV con dividendos. Por defecto: "../data/dividends.csv"
        
        Formato esperado del CSV:
        -------------------------
        ticker,dividends_2025
        AAPL,"0.25,0.26,0.26,0.26"
        REP.MC,"0.55"
        
        Return:
        --------
        pd.Series : dividend_yield por ticker (dividendos_totales / S0)
        """
        if self.S0 is None:
            raise ValueError("Primero debes ejecutar seleccionar_adj_close()")

        df_div = pd.read_csv(dividends_csv)
        
        def sumar_dividendos(div_str):
            if pd.isna(div_str) or div_str == "":
                return 0.0
            if isinstance(div_str, str) and ',' in div_str:
                return sum(float(x.strip()) for x in div_str.strip('"').split(','))
            return float(div_str.strip('"'))
        
        df_div['div_total'] = df_div['dividends_2025'].apply(sumar_dividendos)
        
        dividend_yield = {}
        for ticker in self.S0.index:
            if ticker in df_div['ticker'].values:
                div_total = df_div[df_div['ticker'] == ticker]['div_total'].iloc[0]
                dividend_yield[ticker] = div_total / self.S0[ticker]
            else:
                print(f"⚠️ Ticker {ticker} no encontrado en dividends.csv → yield=0")
                dividend_yield[ticker] = 0.0
        
        self.dividend_yield = pd.Series(dividend_yield)
        return self.dividend_yield

    def procesar_pipeline(self, fecha_valoracion, dividends_csv="../data/dividends.csv", 
                        window=100, min_obs=30, metodo_proxy="promedio"):
        """
        Pipeline completo en un método.
        """
        self.filtrar_fecha(fecha_valoracion)
        self.seleccionar_adj_close()
        self.calcular_retornos_log(window=window, min_obs=min_obs)
        self.estimar_volatilidad()
        self.asignar_volatilidad_proxy(self.sigma_annual, min_obs=min_obs, metodo=metodo_proxy)
        self.calcular_dividend_yield(dividends_csv)
        
        return self.resumen()
    def resumen(self):
        """Resumen rápido de parámetros calculados."""
        return {
            "S0": self.S0,
            "log_returns": self.log_returns,
            "sigma_daily": self.sigma_daily,
            "d": self.dividend_yield,
            "sigma_annual": self.sigma_annual
        }

