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
import matplotlib
matplotlib.use("Agg")   # genera los PNG sin abrir ventanas (sirve en cualquier compu)
import matplotlib.pyplot as plt
from matplotlib import font_manager

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

# Carpeta donde se guardan los gráficos para la presentación
CARPETA_GRAFICOS = os.path.join(BASE, "graficos")
os.makedirs(CARPETA_GRAFICOS, exist_ok=True)


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
# 4. VISUALIZACIÓN
# Todos los gráficos usan la identidad visual de OFCA y se guardan
# como PNG en la carpeta "graficos/" para usarlos en la presentación.
# ============================================================

# Paleta OFCA (guía de estilo + colores del logo)
AMARILLO = "#F2D565"      # acento: destacar un valor
CELESTE = "#7BB6D1"       # serie principal
GRIS_AZULADO = "#93AAB5"  # series secundarias y grillas
GRIS_OSCURO = "#272F33"   # texto y ejes
AZUL_MARINO = "#14284B"   # títulos y serie fuerte
FUENTE_DATOS = "Fuente: ANAC / Secretaría de Turismo - datos.yvera.gob.ar/dataset/conectividad-aerea"

# Umbrales de interpretación del Load Factor (ver CLAUDE.md)
LF_ALTO = 88   # LF sostenido arriba de esto = demanda cerca del techo
LF_BAJO = 75   # LF debajo de esto = sobreoferta


def elegir_tipografia():
    """Usa Montserrat si está instalada; si no, Encode Sans; si no, una sans-serif
    común. Así el script nunca se rompe por falta de una fuente."""
    instaladas = {f.name for f in font_manager.fontManager.ttflist}
    for fuente in ["Montserrat", "Encode Sans"]:
        if fuente in instaladas:
            return fuente
    return "DejaVu Sans"   # viene con matplotlib, siempre está


# Estilo general: se configura una sola vez y aplica a todos los gráficos
plt.rcParams.update({
    "font.family": elegir_tipografia(),
    "text.color": GRIS_OSCURO,
    "axes.labelcolor": GRIS_OSCURO,
    "axes.edgecolor": GRIS_AZULADO,
    "xtick.color": GRIS_OSCURO,
    "ytick.color": GRIS_OSCURO,
    "axes.spines.top": False,      # sin bordes de arriba ni de la derecha
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRIS_AZULADO,
    "grid.alpha": 0.3,
    "axes.axisbelow": True,        # la grilla queda detrás de las barras
    "axes.titlepad": 16,           # aire entre el título y el gráfico
    "figure.facecolor": "white",
})


def miles(valor):
    """Formatea un número con punto de miles, al estilo argentino (1.234.567)."""
    return f"{valor:,.0f}".replace(",", ".")


def abreviar_ruta(ruta):
    """Acorta los nombres largos solo para las etiquetas de los gráficos."""
    return ruta.replace("Ciudad de Buenos Aires", "CABA")


def guardar_grafico(fig, nombre_archivo):
    """Agrega la fuente abajo a la izquierda, guarda el PNG y cierra la figura."""
    fig.text(0.01, 0.01, FUENTE_DATOS, fontsize=8, color=GRIS_AZULADO)
    ruta = os.path.join(CARPETA_GRAFICOS, nombre_archivo)
    fig.savefig(ruta, dpi=200, bbox_inches="tight")
    plt.close(fig)   # libera memoria
    print("Gráfico guardado:", ruta)


# ------------------------------------------------------------
# 4.1 Evolución anual de pasajeros
# 2026 se pinta distinto porque solo tiene enero-julio: no es comparable
# con los años completos y así no se lee como una "caída".
# ------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5.5))
anios = lf_anual.index.astype(str).tolist()
millones = lf_anual["pasajeros"] / 1e6
colores = [CELESTE] * len(anios)
etiquetas_x = anios.copy()
if lf_anual.index.max() == 2026:
    colores[-1] = GRIS_AZULADO
    etiquetas_x[-1] = "2026\n(ene-jul)"

barras = ax.bar(etiquetas_x, millones, color=colores, width=0.6)
ax.set_ylim(0, millones.max() * 1.15)   # espacio arriba para las etiquetas
# Valor arriba de cada barra (son pocas, se leen bien)
for barra, valor in zip(barras, millones):
    ax.text(barra.get_x() + barra.get_width() / 2, valor + millones.max() * 0.02,
            f"{valor:.1f} M".replace(".", ","), ha="center", fontsize=10)

ax.set_title("La demanda de cabotaje se cuadruplicó después de la pandemia",
             fontsize=14, fontweight="bold", color=AZUL_MARINO, loc="left")
ax.set_ylabel("Pasajeros (millones)")
ax.grid(axis="x", visible=False)
guardar_grafico(fig, "01_pasajeros_por_anio.png")


# ------------------------------------------------------------
# 4.2 Evolución anual del Load Factor
# Va en un gráfico aparte (y no con un segundo eje en el de pasajeros)
# porque mezclar dos escalas en un mismo gráfico confunde la lectura.
# ------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5.5))
ax.plot(etiquetas_x, lf_anual["load_factor"], color=AZUL_MARINO, linewidth=2.5,
        marker="o", markersize=8)
for x, valor in zip(etiquetas_x, lf_anual["load_factor"]):
    ax.text(x, valor + 0.4, f"{valor:.1f}%".replace(".", ","), ha="center", fontsize=10)

ax.set_ylim(75, 90)   # se recorta el eje para que se vean las diferencias de 1-2 puntos
ax.set_title("Desde 2022 los aviones viajan con 84%-86% de sus asientos ocupados",
             fontsize=14, fontweight="bold", color=AZUL_MARINO, loc="left")
ax.set_ylabel("Load Factor (%)")
guardar_grafico(fig, "02_load_factor_por_anio.png")


# ------------------------------------------------------------
# 4.3 Estacionalidad: Load Factor por mes
# Se resalta en amarillo el mes con el LF más alto.
# ------------------------------------------------------------
NOMBRES_MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                 "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

fig, ax = plt.subplots(figsize=(10, 5.5))
nombres = [NOMBRES_MESES[m - 1] for m in lf_mes.index]
mes_pico = lf_mes["load_factor"].idxmax()
colores = [AMARILLO if m == mes_pico else CELESTE for m in lf_mes.index]

ax.bar(nombres, lf_mes["load_factor"], color=colores, width=0.65)
for x, valor in zip(nombres, lf_mes["load_factor"]):
    ax.text(x, valor + 0.15, f"{valor:.1f}".replace(".", ","), ha="center", fontsize=9)

ax.set_ylim(78, 90)
ax.set_title("El Load Factor sube en primavera y verano y baja en otoño",
             fontsize=14, fontweight="bold", color=AZUL_MARINO, loc="left")
ax.set_ylabel("Load Factor (%) - promedio 2020-2026")
ax.grid(axis="x", visible=False)
guardar_grafico(fig, "03_estacionalidad_load_factor.png")


# ------------------------------------------------------------
# 4.4 Ranking: las 15 rutas más llenas de 2025
# Barras horizontales porque los nombres de las rutas son largos.
# ------------------------------------------------------------
top_lf = rutas.sort_values("load_factor", ascending=False).head(15)
top_lf = top_lf.sort_values("load_factor")   # la más alta queda arriba del gráfico

fig, ax = plt.subplots(figsize=(10, 7))
nombres = [abreviar_ruta(r) for r in top_lf.index]
ax.barh(nombres, top_lf["load_factor"], color=CELESTE, height=0.65)
for y, valor in zip(nombres, top_lf["load_factor"]):
    ax.text(valor + 0.1, y, f"{valor:.1f}%".replace(".", ","), va="center", fontsize=9)

# Línea de referencia: el umbral de "ruta muy llena"
ax.axvline(LF_ALTO, color=AZUL_MARINO, linestyle="--", linewidth=1.2)
ax.text(LF_ALTO, len(top_lf) - 0.4, f" umbral {LF_ALTO}%", color=AZUL_MARINO, fontsize=9)

ax.set_xlim(top_lf["load_factor"].min() - 3, top_lf["load_factor"].max() + 1.5)
ax.set_title(f"Las rutas más llenas de 2025 son destinos turísticos desde Aeroparque\n"
             f"(rutas con al menos {MIN_VUELOS} vuelos en el año)",
             fontsize=13, fontweight="bold", color=AZUL_MARINO, loc="left")
ax.set_xlabel("Load Factor 2025 (%)")
ax.grid(axis="y", visible=False)
guardar_grafico(fig, "04_top_rutas_load_factor_2025.png")


# ------------------------------------------------------------
# 4.5 Matriz volumen vs Load Factor (2025)
# Cada punto es una ruta. Arriba a la derecha están las rutas con mucha
# demanda Y aviones llenos: las candidatas a sumar frecuencias.
# "Mucho volumen" = más pasajeros que la mediana de las rutas analizadas.
# ------------------------------------------------------------
volumen_alto = rutas["pasajeros"].median()
es_candidata = (rutas["load_factor"] >= LF_ALTO) & (rutas["pasajeros"] >= volumen_alto)
candidatas = rutas[es_candidata]
resto = rutas[~es_candidata]

fig, ax = plt.subplots(figsize=(11, 7))
ax.scatter(resto["pasajeros"] / 1000, resto["load_factor"], s=40,
           color=GRIS_AZULADO, alpha=0.7, label="Resto de las rutas")
ax.scatter(candidatas["pasajeros"] / 1000, candidatas["load_factor"], s=70,
           color=AZUL_MARINO, edgecolor="white", linewidth=1.5,
           label=f"Candidatas: LF ≥ {LF_ALTO}% y volumen alto")

# Nombre de cada candidata al lado de su punto (son pocas).
# Se alternan arriba y abajo del punto para que no se pisen entre sí.
candidatas_ordenadas = candidatas.sort_values("pasajeros")
for i, (ruta, fila) in enumerate(candidatas_ordenadas.iterrows()):
    desplazamiento = 8 if i % 2 == 0 else -14
    ax.annotate(abreviar_ruta(ruta), (fila["pasajeros"] / 1000, fila["load_factor"]),
                xytext=(0, desplazamiento), textcoords="offset points",
                ha="center", fontsize=8, color=GRIS_OSCURO)

# Líneas de referencia que arman los "cuadrantes"
ax.axhline(LF_ALTO, color=AZUL_MARINO, linestyle="--", linewidth=1)
ax.axhline(LF_BAJO, color=GRIS_AZULADO, linestyle="--", linewidth=1)
ax.axvline(volumen_alto / 1000, color=GRIS_AZULADO, linestyle=":", linewidth=1)
ax.text(ax.get_xlim()[1], LF_BAJO - 1, f"debajo de {LF_BAJO}%: sobreoferta ",
        ha="right", fontsize=9, color=GRIS_OSCURO)

ax.set_title("Rutas con mucha demanda y aviones llenos: candidatas a sumar frecuencias (2025)",
             fontsize=13, fontweight="bold", color=AZUL_MARINO, loc="left")
ax.set_xlabel("Pasajeros en 2025 (miles)")
ax.set_ylabel("Load Factor 2025 (%)")
ax.legend(loc="lower right", frameon=False)
guardar_grafico(fig, "05_matriz_volumen_vs_load_factor.png")

print("\n=== Rutas candidatas a sumar frecuencias (2025) ===")
print(candidatas.sort_values("pasajeros", ascending=False))
# Conclusión parcial: las candidatas combinan mucho tráfico y LF ≥ 88%.
# Son rutas donde la demanda ya está cerca del techo de la oferta actual:
# sumar frecuencias ahí tiene menos riesgo de que los vuelos salgan vacíos.
