# ============================================================
# OFCA - Observatorio Federal de Conectividad Aérea
# "Todo el país, más cerca"
#
# TPO Taller de Programación II - UADE - Grupo 10
# Integrantes: Luciana Pirruccio, Agostina Pacheco, Sebastián Gómez Martínez
#
# Tema: demanda histórica y factor de ocupación (Load Factor) en las rutas
# aéreas de cabotaje de Argentina (2020-2026), para detectar cuellos de
# botella y evaluar dónde conviene sumar frecuencias.
#
# Fuente: Secretaría de Turismo - Conectividad Aérea (datos de la ANAC / SIAC)
# https://datos.yvera.gob.ar/dataset/conectividad-aerea
# ============================================================
import os
import requests
import pandas as pd

# ------------------------------------------------------------
# CONFIGURACIÓN
# Carpeta "data" al lado de este .py (funciona en cualquier compu)
# ------------------------------------------------------------
try:
    BASE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE = os.getcwd()   # por si se corre desde un notebook

CARPETA_DATA = os.path.join(BASE, "data")
os.makedirs(CARPETA_DATA, exist_ok=True)

URL_TURISMO = ("https://datos.yvera.gob.ar/dataset/c0e7bc3d-553c-405c-8b32-79282b28ffd5/"
               "resource/aab49234-28c9-48ab-a978-a83485139290/download/base_microdatos.csv")
RUTA_TURISMO = os.path.join(CARPETA_DATA, "base_microdatos.csv")


# ============================================================
# 1. EXTRACCIÓN
# ============================================================
def descargar_csv(url, ruta_destino):
    """Descarga un CSV con requests y lo guarda en disco.
    Si el archivo ya existe, no lo vuelve a descargar."""
    if os.path.exists(ruta_destino):
        print(f"Ya existe: {ruta_destino}")
        return

    print("Descargando... (puede tardar, el archivo es grande)")
    # stream=True: baja el archivo de a pedazos, sin cargarlo entero en memoria
    with requests.get(url, stream=True, timeout=300) as resp:
        resp.raise_for_status()   # corta si hay error (404, 500, etc.)
        with open(ruta_destino, "wb") as f:
            for bloque in resp.iter_content(chunk_size=1024 * 1024):   # bloques de 1 MB
                f.write(bloque)

    tamanio_mb = os.path.getsize(ruta_destino) / 1e6
    print(f"Descargado: {ruta_destino} ({tamanio_mb:.1f} MB)")


descargar_csv(URL_TURISMO, RUTA_TURISMO)

try:
    df_tur = pd.read_csv(RUTA_TURISMO, low_memory=False)
except UnicodeDecodeError:
    df_tur = pd.read_csv(RUTA_TURISMO, encoding="latin-1", low_memory=False)

df_tur["indice_tiempo"] = pd.to_datetime(df_tur["indice_tiempo"])

print("Filas y columnas:", df_tur.shape)
print("Desde:", df_tur["indice_tiempo"].min().date(), "Hasta:", df_tur["indice_tiempo"].max().date())
# Resultado: 1.078.289 filas, de 2017-01-01 a 2026-07-31.
# Ojo: Excel solo muestra 1.048.576 filas, por eso al abrirlo ahí se perdía lo último.


# ============================================================
# 2. VALIDACIÓN Y LIMPIEZA
# ============================================================

# Período de análisis: 2020 en adelante
df = df_tur[df_tur["indice_tiempo"].dt.year >= 2020].copy()

# Solo cabotaje (vuelos dentro de Argentina) y solo vuelos regulares.
# Los no regulares (chárter) se venden completos y distorsionan la demanda normal.
df = df[(df["clasificacion_vuelo"] == "Cabotaje") & (df["clase_vuelo"] == "Regular")]

# Controles de calidad
print("Nulos:", df[["pasajeros", "asientos", "vuelos"]].isna().sum().sum())
print("Filas con asientos = 0:", (df["asientos"] == 0).sum())
print("Filas con más pasajeros que asientos:", (df["pasajeros"] > df["asientos"]).sum())

# Sacamos filas inválidas (en la práctica hubo 0: la base viene prolija)
df = df.dropna(subset=["pasajeros", "asientos", "vuelos"])
df = df[(df["asientos"] > 0) & (df["pasajeros"] <= df["asientos"])]

# Columnas auxiliares
df["anio"] = df["indice_tiempo"].dt.year
df["mes"] = df["indice_tiempo"].dt.month
# La ruta tiene sentido: "A - B" no es lo mismo que "B - A"
df["ruta"] = df["origen_localidad"] + " - " + df["destino_localidad"]

print("Filas después de limpiar:", len(df))   # 370.950

# Guardamos la versión limpia
df.to_csv(os.path.join(CARPETA_DATA, "cabotaje_limpio_2020_2026.csv"), index=False)


# ============================================================
# 3. ANÁLISIS
# Load Factor = pasajeros totales / asientos totales.
# Siempre se suma primero y después se divide (no se promedian LF de filas).
# ============================================================
def calcular_lf(agrupado):
    """Recibe un DataFrame con pasajeros/asientos sumados y agrega el Load Factor (%)."""
    agrupado["load_factor"] = (agrupado["pasajeros"] / agrupado["asientos"] * 100).round(1)
    return agrupado


# 3.1 Load Factor por año
lf_anual = calcular_lf(df.groupby("anio")[["pasajeros", "asientos", "vuelos"]].sum())
print("\n=== Load Factor por año ===")
print(lf_anual)
# Conclusión parcial: la demanda se cuadruplicó tras la pandemia (3,6 M en 2020
# a 17,2 M en 2023 y 2025). El LF se mantiene alto, entre 84% y 86%, desde 2022.

# 3.2 Comparación justa enero-julio (2026 solo llega hasta julio)
ene_jul = calcular_lf(df[df["mes"] <= 7].groupby("anio")[["pasajeros", "asientos", "vuelos"]].sum())
ene_jul["var_pasajeros_%"] = (ene_jul["pasajeros"].pct_change() * 100).round(1)
print("\n=== Enero-Julio de cada año ===")
print(ene_jul)
# Conclusión parcial: en 2026 viajó 5,5% menos gente que en 2025 (ene-jul),
# pero el LF subió a 86,2%: hay menos asientos ofrecidos y van más llenos.

# 3.3 Estacionalidad: Load Factor por mes (todos los años juntos)
lf_mes = calcular_lf(df.groupby("mes")[["pasajeros", "asientos"]].sum())
print("\n=== Load Factor por mes ===")
print(lf_mes)
# Conclusión parcial: picos en octubre-noviembre y febrero; mínimos en abril-mayo.

# 3.4 Load Factor por ruta (2025, último año completo)
# Mínimo de 300 vuelos en el año para no sacar conclusiones de rutas chicas
MIN_VUELOS = 300
df_2025 = df[df["anio"] == 2025]

rutas = calcular_lf(df_2025.groupby("ruta")[["pasajeros", "asientos", "vuelos"]].sum())
rutas = rutas[rutas["vuelos"] >= MIN_VUELOS]

print("\n=== Top 15 rutas con MAYOR Load Factor (2025) ===")
print(rutas.sort_values("load_factor", ascending=False).head(15))
print("\n=== Top 15 rutas con MÁS pasajeros (2025) ===")
print(rutas.sort_values("pasajeros", ascending=False).head(15))
# Conclusión parcial: las rutas más llenas (más de 88%) son destinos turísticos
# conectados con Aeroparque: El Calafate, Salta, Iguazú, Tucumán, Bariloche, Ushuaia.

# 3.5 Load Factor por aeropuerto de destino (2025)
aeropuertos = calcular_lf(df_2025.groupby("destino_aeropuerto")[["pasajeros", "asientos", "vuelos"]].sum())
aeropuertos = aeropuertos[aeropuertos["vuelos"] >= MIN_VUELOS]
print("\n=== Aeropuertos de destino por Load Factor (2025) ===")
print(aeropuertos.sort_values("load_factor", ascending=False).head(15))


# ============================================================
# 4. VISUALIZACIÓN (próximo paso)
# Paleta OFCA: #F2D565 (amarillo), #7BB6D1 (celeste), #93AAB5 (gris azulado),
# #272F33 (gris oscuro), #14284B (azul marino del logo)
# ============================================================
