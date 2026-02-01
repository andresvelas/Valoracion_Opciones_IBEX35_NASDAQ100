import pandas as pd
import numpy as np
import yfinance as yf

class PreprocesamientoIBEX35:
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
        
        # Seleccionar Adj Close y eliminar columnas completamente vacías
        self.adj_close = self.df_filtrado["Adj Close"].dropna(how='all')
        
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
        
        # Detectar tickers con menos de min_obs precios
        for ticker in self.adj_close.columns:
            n_precios = self.adj_close[ticker].dropna().shape[0]
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
    def calcular_dividend_yield(self):
        """
        Calcula el dividend yield anualizado por ticker usando yfinance.
        Requiere que se haya ejecutado seleccionar_adj_close() para tener S0.
        
        Devuelve un pd.Series con dividend yield por ticker.
        """
        if self.S0 is None:
            raise ValueError("Primero debes ejecutar seleccionar_adj_close() para tener S0")

        dividend_yield = pd.Series(index=self.adj_close.columns, dtype=float)

        for ticker in self.adj_close.columns:
            try:
                # Preprocesamiento básico: strip, mayúsculas, y formato válido para yfinance
                yf_ticker_str = ticker.strip().upper()
                
                # Algunos tickers del IBEX35 terminan en .MC, lo dejamos tal cual
                # Puedes añadir reglas aquí si algún ticker falla
                
                # Descargar dividendos
                yf_ticker = yf.Ticker(yf_ticker_str)
                divs = yf_ticker.dividends  # Series con fechas como índice
                
                if divs.empty:
                    print(f"⚠️ {ticker} no tiene dividendos en yfinance.")
                    dividend_yield[ticker] = 0.0
                    continue

                # Últimos 12 meses
                fecha_max = self.df_filtrado.index.max()
                fecha_min = fecha_max - pd.DateOffset(years=1)
                divs_ultimo_anio = divs[(divs.index > fecha_min) & (divs.index <= fecha_max)]

                dividend_total = divs_ultimo_anio.sum()
                dividend_yield[ticker] = dividend_total / self.S0[ticker]

            except Exception as e:
                print(f"⚠️ No se pudo obtener dividendos para {ticker}: {e}")
                dividend_yield[ticker] = np.nan

        self.dividend_yield = dividend_yield
        return self.dividend_yield

    def resumen(self):
        """Resumen rápido de parámetros calculados."""
        return {
            "S0": self.S0,
            "log_returns": self.log_returns,
            "sigma_daily": self.sigma_daily,
            "sigma_annual": self.sigma_annual
        }

