import numpy as np
import scipy.stats as si

class MotorValoracion:
    def __init__(self, S0, K, T, r, sigma, d, semilla=123456789):
        self.S0 = S0
        self.K = K
        self.T = T
        self.r = r
        self.sigma = sigma
        self.d = d
        self.semilla = semilla
        
    def box_muller(self, n_total):
        """Genera n_total variables N(0,1) usando el generador congruencial."""
        m=2**(31)-1
        a=16807
        b=0


        def generador():
            x = self.semilla
            while True:
                x = (a * x + b) % m
                yield x / m
        
        g = generador()
        U = [next(g) for _ in range(n_total * 2)]
        u1, u2 = np.array(U[0::2]), np.array(U[1::2])
        
        z0 = np.sqrt(-2.0 * np.log(u1)) * np.cos(2.0 * np.pi * u2)
        return z0 

    def metodo_black_scholes(self):
        """Solución analítica Black-Scholes-Merton."""
        d1 = (np.log(self.S0 / self.K) + (self.r - self.d + 0.5 * self.sigma**2) * self.T) / (self.sigma * np.sqrt(self.T))
        d2 = d1 - self.sigma * np.sqrt(self.T)
        
        c = (self.S0 * np.exp(-self.d * self.T) * si.norm.cdf(d1) - 
             self.K * np.exp(-self.r * self.T) * si.norm.cdf(d2))
        p = (self.K * np.exp(-self.r * self.T) * si.norm.cdf(-d2) - 
             self.S0 * np.exp(-self.d * self.T) * si.norm.cdf(-d1))
        return {"call": c, "put": p}

    def metodo_binomial(self, N=100):
        """Árbol binomial con modelo Cox-Ross-Rubinstein."""
        dt = self.T / N
        u = np.exp(self.sigma * np.sqrt(dt))
        d = 1 / u
        # Probabilidad neutral al riesgo ajustada por dividendos
        q = (np.exp((self.r - self.d) * dt) - d) / (u - d)
        
        # Precios finales del subyacente
        S_T = self.S0 * (u ** np.arange(N, -1, -1)) * (d ** np.arange(0, N + 1))

        C = np.maximum(S_T - self.K, 0)
        P = np.maximum(self.K - S_T, 0)

        disc = np.exp(-self.r * dt)
        for i in range(N - 1, -1, -1):
            C = disc * (q * C[:-1] + (1 - q) * C[1:])
            P = disc * (q * P[:-1] + (1 - q) * P[1:])
            
        return {"call": C[0], "put": P[0]}

    def metodo_montecarlo(self, n_caminos=1000, dt=1/52):
        """Simulación dinámica mediante la ecuación estocástica proporcionada."""
        M = int(self.T / dt) # Número de pasos
        Z = self.box_muller(n_caminos * M).reshape(n_caminos, M)
        

        S_t = np.ones(n_caminos) * self.S0
        
        for t in range(M):
            S_t = S_t * (1 + self.r - self.d)**dt + self.sigma * S_t * np.sqrt(dt) * Z[:, t]
        
        payoff_call = np.maximum(S_t - self.K, 0)
        payoff_put = np.maximum(self.K - S_t, 0)
        
        disc = np.exp(-self.r * self.T)
        return {
            "call": disc * np.mean(payoff_call),
            "put": disc * np.mean(payoff_put),
            "error_std_call": disc * np.std(payoff_call) / np.sqrt(n_caminos)
        }