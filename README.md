## 1. Selección de subyacentes

Para la realización de la práctica se ha trabajado con la **lista de activos proporcionada oficialmente para la práctica 2026**, por lo que no se ha realizado una selección adicional de subyacentes.

Los activos analizados se dividen en dos grupos: acciones pertenecientes al **IBEX 35** y acciones pertenecientes al **NASDAQ 100**.

### 1.1 Subyacentes del IBEX 35

Los subyacentes seleccionados del índice IBEX 35 son los siguientes:

- Repsol (REP.MC)  
- Inditex (ITX.MC)  
- Endesa (ELE.MC)  
- Acerinox (ACX.MC)  
- Logista (LOG.MC)  
- Ferrovial (FER.MC)  
- Banco Santander (SAN.MC)  
- BBVA (BBVA.MC)  
- Indra (IDR.MC)  
- Aena (AENA.MC)  
- Iberdrola (IBE.MC)  
- Acciona (ANA.MC)  
- Sacyr (SCYR.MC)  
- Telefónica (TEF.MC)  

### 1.2 Subyacentes del NASDAQ 100

Los subyacentes seleccionados del índice NASDAQ 100 son:

- Apple (AAPL)  
- NVIDIA (NVDA)  
- Adobe (ADBE)  
- Intel (INTC)  
- Costco Wholesale (COST)  
- Warner Bros. Discovery (WBD)  
- Tesla (TSLA)  
- GE HealthCare Technologies (GEHC)  
- Meta Platforms (META)  
- Airbnb (ABNB)  
- PepsiCo (PEP)  
- Monster Beverage (MNST)  
- Netflix (NFLX)  

Estos subyacentes constituyen el conjunto de activos sobre los que se llevará a cabo la valoración de opciones call y put europeas mediante simulación Monte Carlo, árbol binomial y la solución analítica de Black-Scholes.

## Estructura del Proyecto

El proyecto está organizado de forma modular para separar la lógica de procesamiento, los datos brutos y el análisis final.

```text
.
├── 📁 data                   # Almacén de datos (Brutos y Procesados)
│   ├── dividends.csv         # Datos de rentabilidad por dividendo
│   ├── option_chains_all.csv # Cadena de opciones original (Raw)
│   ├── opciones_preprocesadas.csv # Resultado tras limpieza de fechas/strikes
│   └── *.pkl                 # Objetos serializados (resumen_activos, etc.)
│
├── 📁 src                    # Núcleo del Código (Scripts .py)
│   ├── PreprocesamientoActivos.py  # Lógica de limpieza de tickers y volatilidad
│   ├── PreprocesamientoOpciones.py # Lógica de filtrado de contratos y tiempos
│   └── Valoracion.py               # Clase MotorValoracion (BS, Binomial, MC)
│
├── 📁 notebooks              # Fase de Ejecución y Análisis
│   ├── 01_preprocesamiento.ipynb   # Limpieza inicial de activos del IBEX y NASDAQ
│   ├── 02_preprocesamiento.ipynb   # Preparación de la cadena de opciones
│   └── 03_estudio.ipynb            # Generación de resultados y comparativa final
│
├── 📁 reports                # Salidas del estudio (Tablas y Gráficos)
├── setup.py                  # Configuración para instalación como paquete
└── README.md                 # Documentación principal

