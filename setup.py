from setuptools import setup, find_packages
import os


name = 'Andrés Velasco'
email = 'andres.velasco.sanchez.2023@gmail.com'

setup(
    name='Proyecto de Valoracion de Opciones - IBEX 35 y NASDAQ 100',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'numpy>=1.24.0',
        'pandas>=2.1.0',
        'matplotlib>=3.7.1',
        'plotly>=6.0.0',
        'nbformat>=4.2.0',       
        'ipywidgets>=7.5',
        'yfinance>=0.2.0',
        'scipy',
        'seaborn'
    ],
    author=name,
    author_email=email,
    description='Paquetes para Proyecto de Valoración de Opciones - IBEX 35 y NASDAQ 100'  
)
