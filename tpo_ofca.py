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
# Fuentes:
# 1) Secretaría de Turismo - Conectividad Aérea (datos de la ANAC / SIAC)
#    https://datos.yvera.gob.ar/dataset/conectividad-aerea
# 2) ANAC - Aterrizajes y despegues procesados (un CSV por año)
#    https://datos.gob.ar/dataset/aterrizajes-y-despegues-procesados-por-la-administracion-nacional-de-aviacion-civil-anac
# ============================================================
import os
import requests
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # genera los PNG sin abrir ventanas (sirve en cualquier compu)
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch

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


# ============================================================
# 5. SEGUNDA FUENTE: ANAC - ATERRIZAJES Y DESPEGUES
# https://datos.gob.ar/dataset/aterrizajes-y-despegues-procesados-por-la-administracion-nacional-de-aviacion-civil-anac
#
# ¿Para qué la sumamos? La base de Turismo tiene asientos (sirve para el
# Load Factor) pero no tiene la HORA de los vuelos. La de ANAC registra cada
# aterrizaje y despegue con su hora y sus pasajeros. Con eso podemos ver:
#   - cuántos pasajeros recibe cada aeropuerto por vuelo,
#   - en qué horas se concentran los vuelos (cuellos de botella).
# ============================================================
CARPETA_ANAC = os.path.join(CARPETA_DATA, "anac")
os.makedirs(CARPETA_ANAC, exist_ok=True)

ANIOS_ANAC = [2020, 2021, 2022, 2023, 2024, 2025, 2026]

# El portal de Transporte (donde están guardados los archivos) tiene una API
# que devuelve la lista de archivos del dataset con sus links de descarga.
# La usamos porque el nombre del archivo de cada año cambia cuando ANAC lo actualiza.
URL_API_ANAC = ("https://datos.transporte.gob.ar/api/3/action/package_show"
                "?id=21038a1a-c3c7-4494-b76a-3a2a8fbb83b5")


# ------------------------------------------------------------
# 5.1 EXTRACCIÓN
# ------------------------------------------------------------
def buscar_urls_anac():
    """Le pregunta a la API del portal qué archivos tiene el dataset y
    devuelve un diccionario {año: link de descarga del CSV}."""
    resp = requests.get(URL_API_ANAC, timeout=60)
    resp.raise_for_status()
    recursos = resp.json()["result"]["resources"]

    urls = {}
    for recurso in recursos:
        texto = (recurso.get("name", "") + " " + recurso.get("url", "")).lower()
        if not recurso.get("url", "").lower().endswith(".csv"):
            continue   # solo nos interesan los CSV
        for anio in ANIOS_ANAC:
            if str(anio) in texto and anio not in urls:
                urls[anio] = recurso["url"]
    return urls


def descargar_anac():
    """Descarga un CSV por año a data/anac/. Si ya están, no hace nada."""
    faltantes = [a for a in ANIOS_ANAC
                 if not os.path.exists(os.path.join(CARPETA_ANAC, f"anac_{a}.csv"))]
    if not faltantes:
        print("Los CSV de ANAC ya están descargados.")
        return

    # Si el portal no responde, el script sigue con los años que ya estén descargados
    try:
        urls = buscar_urls_anac()
    except requests.exceptions.RequestException as error:
        print("No se pudo consultar el portal de ANAC:", error)
        urls = {}

    for anio in faltantes:
        if anio not in urls:
            print(f"No se encontró el CSV de ANAC {anio} en el portal. "
                  f"Descargarlo a mano y guardarlo como data/anac/anac_{anio}.csv")
            continue
        print(f"ANAC {anio}: {urls[anio]}")
        descargar_csv(urls[anio], os.path.join(CARPETA_ANAC, f"anac_{anio}.csv"))


descargar_anac()


# ------------------------------------------------------------
# 5.2 LECTURA, VALIDACIÓN Y LIMPIEZA
# Los archivos de ANAC vienen con separador ";" y la coma como decimal
# (ej: "167,00"). Además, los nombres de las columnas cambian un poco
# entre años, así que los pasamos a nombres fijos antes de unirlos.
# ------------------------------------------------------------
def nombre_estandar(columna):
    """Traduce el nombre de una columna de ANAC a un nombre corto y fijo."""
    col = columna.strip().lower()
    if col.startswith("fecha"):
        return "fecha"
    if col.startswith("hora"):
        return "hora_utc"
    if col.startswith("clase de vuelo"):
        return "clase_vuelo"
    if col.startswith("clasificaci"):
        return "clasificacion_vuelo"
    if col.startswith("tipo de movimiento"):
        return "movimiento"
    if col == "aeropuerto":
        return "aeropuerto"
    if col.startswith("origen"):
        return "origen_destino"
    if col == "pasajeros":
        return "pasajeros"
    return col   # las demás columnas no las usamos


COLUMNAS_ANAC = ["fecha", "hora_utc", "clase_vuelo", "clasificacion_vuelo",
                 "movimiento", "aeropuerto", "origen_destino", "pasajeros"]


def leer_anac(anio):
    """Lee el CSV de un año y devuelve solo las columnas que usamos."""
    ruta = os.path.join(CARPETA_ANAC, f"anac_{anio}.csv")
    try:
        datos = pd.read_csv(ruta, sep=";", decimal=",", low_memory=False)
    except UnicodeDecodeError:
        datos = pd.read_csv(ruta, sep=";", decimal=",", encoding="latin-1", low_memory=False)

    datos.columns = [nombre_estandar(c) for c in datos.columns]
    faltan = [c for c in COLUMNAS_ANAC if c not in datos.columns]
    if faltan:
        print(f"ANAC {anio}: faltan las columnas {faltan}. Revisar el archivo.")
        return None
    print(f"ANAC {anio}: {len(datos):,} filas".replace(",", "."))
    return datos[COLUMNAS_ANAC]


anuales = [leer_anac(a) for a in ANIOS_ANAC
           if os.path.exists(os.path.join(CARPETA_ANAC, f"anac_{a}.csv"))]
anac = pd.concat([d for d in anuales if d is not None], ignore_index=True)
print("ANAC - filas totales:", len(anac))

# Solo vuelos de cabotaje (ANAC los llama "Doméstico") y regulares,
# igual que hicimos con la base de Turismo.
anac = anac[anac["clasificacion_vuelo"].isin(["Doméstico", "Cabotaje"])]
anac = anac[anac["clase_vuelo"] == "Regular"].copy()

# La hora viene en UTC. Argentina es UTC-3, así que restamos 3 horas
# (si no, el "pico de las 10" sería en realidad a las 7 de la mañana).
anac["pasajeros"] = pd.to_numeric(anac["pasajeros"], errors="coerce")
hora = pd.to_numeric(anac["hora_utc"].astype(str).str.split(":").str[0], errors="coerce")
fecha = pd.to_datetime(anac["fecha"], dayfirst=True, format="mixed", errors="coerce")
anac["fecha_hora"] = fecha + pd.to_timedelta(hora, unit="h") - pd.Timedelta(hours=3)

# Controles de calidad
print("ANAC - fechas u horas que no se pudieron leer:", anac["fecha_hora"].isna().sum())
print("ANAC - filas sin pasajeros informados:", anac["pasajeros"].isna().sum())
print("ANAC - vuelos regulares con 0 pasajeros:", (anac["pasajeros"] == 0).sum())

# Sacamos filas inválidas. Los vuelos regulares con 0 pasajeros son pocos
# (~1%) y suelen ser datos sin cargar: si los dejamos, bajan el promedio
# de pasajeros por vuelo sin que eso refleje la demanda real.
anac = anac.dropna(subset=["fecha_hora", "pasajeros"])
anac = anac[anac["pasajeros"] > 0]

anac["anio"] = anac["fecha_hora"].dt.year
anac["hora"] = anac["fecha_hora"].dt.hour
# Por la resta de 3 horas, los vuelos de la madrugada del 1/1 caen en el
# año anterior: nos quedamos solo con el período de análisis.
anac = anac[anac["anio"].isin(ANIOS_ANAC)]
print("ANAC - filas después de limpiar:", len(anac))

# Control cruzado con la base de Turismo: cada vuelo aparece dos veces en ANAC
# (despegue en el origen y aterrizaje en el destino), así que para contar
# pasajeros del país hay que mirar un solo tipo de movimiento.
control = anac[anac["movimiento"] == "Despegue"].groupby("anio")["pasajeros"].sum() / 1e6
print("\n=== Control: pasajeros (millones) según ANAC vs Turismo ===")
print(pd.DataFrame({"ANAC": control.round(1), "Turismo": (lf_anual["pasajeros"] / 1e6).round(1)}))
# En 2025 dan 17,2 M en las dos bases: las dos fuentes son coherentes.


# ------------------------------------------------------------
# 5.3 ANÁLISIS POR AEROPUERTO
# ANAC usa códigos propios de 3 letras. Este diccionario les pone nombre
# y los une con el código internacional (OACI) que usa la base de Turismo.
# ------------------------------------------------------------
AEROPUERTOS = {
    # código ANAC: (nombre para los gráficos, código OACI)
    "AER": ("Aeroparque (CABA)", "SABE"),
    "EZE": ("Ezeiza", "SAEZ"),
    "CBA": ("Córdoba", "SACO"),
    "DOZ": ("Mendoza", "SAME"),
    "BAR": ("Bariloche", "SAZS"),
    "IGU": ("Puerto Iguazú", "SARI"),
    "NEU": ("Neuquén", "SAZN"),
    "SAL": ("Salta", "SASA"),
    "USU": ("Ushuaia", "SAWH"),
    "TUC": ("Tucumán", "SANT"),
    "ECA": ("El Calafate", "SAWC"),
    "CRV": ("Comodoro Rivadavia", "SAVC"),
    "JUJ": ("Jujuy", "SASJ"),
    "MDP": ("Mar del Plata", "SAZM"),
    "POS": ("Posadas", "SARP"),
    "TRE": ("Trelew", "SAVT"),
    "BCA": ("Bahía Blanca", "SAZB"),
    "CHP": ("San Martín de los Andes", "SAZY"),
    "SIS": ("Resistencia", "SARE"),
    "ROS": ("Rosario", "SAAR"),
    "JUA": ("San Juan", "SANU"),
    "SDE": ("Santiago del Estero", "SANE"),
    "CRR": ("Corrientes", "SARC"),
    "GAL": ("Río Gallegos", "SAWG"),
    "DRY": ("Puerto Madryn", "SAVY"),
    "SVO": ("Santa Fe", "SAAV"),
    "CAT": ("Catamarca", "SANC"),
    "GRA": ("Río Grande", "SAWE"),
    "LAR": ("La Rioja", "SANL"),
    "FSA": ("Formosa", "SARF"),
    "ESQ": ("Esquel", "SAVE"),
    "UIS": ("San Luis", "SAOU"),
    "SRA": ("San Rafael", "SAMR"),
    "PAR": ("Paraná", "SAAP"),
    "OSA": ("Santa Rosa", "SAZR"),
    "VIE": ("Viedma", "SAVV"),
    "TRH": ("Termas de Río Hondo", "SANR"),
    "TRC": ("Río Cuarto", "SAOC"),
}


def nombre_aeropuerto(codigo):
    """Devuelve el nombre del aeropuerto; si no está en el diccionario, el código."""
    return AEROPUERTOS.get(codigo, (codigo, None))[0]


# Pasajeros por vuelo en cada aeropuerto (2025, último año completo).
# Cada fila de ANAC es un vuelo que aterriza o despega en ese aeropuerto,
# así que acá sí sumamos los dos tipos de movimiento.
anac_2025 = anac[anac["anio"] == 2025]
por_aeropuerto = anac_2025.groupby("aeropuerto").agg(
    vuelos=("pasajeros", "size"),
    pasajeros=("pasajeros", "sum"))
por_aeropuerto["pax_por_vuelo"] = (por_aeropuerto["pasajeros"] / por_aeropuerto["vuelos"]).round(1)
por_aeropuerto = por_aeropuerto[por_aeropuerto["vuelos"] >= MIN_VUELOS]

# Load Factor de cada aeropuerto según Turismo (2025): se suman los vuelos
# que salen y los que llegan, y recién después se divide.
salidas = df_2025.groupby("origen_oaci")[["pasajeros", "asientos"]].sum()
llegadas = df_2025.groupby("destino_oaci")[["pasajeros", "asientos"]].sum()
lf_aeropuerto = calcular_lf(salidas.add(llegadas, fill_value=0))

# Unimos las dos fuentes con el código OACI
por_aeropuerto["nombre"] = [nombre_aeropuerto(c) for c in por_aeropuerto.index]
por_aeropuerto["oaci"] = [AEROPUERTOS.get(c, (c, None))[1] for c in por_aeropuerto.index]
por_aeropuerto["load_factor"] = por_aeropuerto["oaci"].map(lf_aeropuerto["load_factor"])
por_aeropuerto = por_aeropuerto.sort_values("pax_por_vuelo", ascending=False)

print("\n=== Aeropuertos: pasajeros por vuelo (ANAC) y Load Factor (Turismo), 2025 ===")
print(por_aeropuerto[["nombre", "vuelos", "pasajeros", "pax_por_vuelo", "load_factor"]])
sin_lf = por_aeropuerto[por_aeropuerto["load_factor"].isna()]
if len(sin_lf) > 0:
    print("Aeropuertos sin Load Factor (no se pudieron unir con Turismo):", list(sin_lf["nombre"]))

# Evolución de pasajeros por vuelo 2020-2026 en los 10 aeropuertos con más vuelos
top10 = por_aeropuerto.sort_values("vuelos", ascending=False).head(10).index
evolucion = anac[anac["aeropuerto"].isin(top10)].groupby(["aeropuerto", "anio"])["pasajeros"].mean()
evolucion = evolucion.round(0).unstack("anio")
evolucion.index = [nombre_aeropuerto(c) for c in evolucion.index]
print("\n=== Pasajeros por vuelo por año (10 aeropuertos con más vuelos) ===")
print(evolucion)

# OJO al interpretar: ANAC no trae asientos. Un aeropuerto puede tener más
# pasajeros por vuelo solo porque llegan aviones más grandes. Por eso lo
# miramos JUNTO con el Load Factor de Turismo: muchos pasajeros por vuelo +
# LF alto = aviones grandes y llenos, la demanda no entra en la oferta actual.
# Conclusión parcial: Bariloche, Iguazú, Ushuaia, Puerto Madryn y San Martín
# de los Andes reciben más pasajeros por vuelo que Aeroparque (158, 148, 147,
# 145 y 144 contra 133). Son destinos turísticos donde cada vuelo trae mucha
# gente. En 2026 Bariloche sube a 168 pasajeros por vuelo.


# ------------------------------------------------------------
# 5.4 CUELLOS DE BOTELLA: ¿A QUÉ HORA SE CONCENTRAN LOS VUELOS?
# Promedio de vuelos (aterrizajes + despegues) por hora del día en 2025.
# ------------------------------------------------------------
dias_2025 = anac_2025["fecha_hora"].dt.date.nunique()
por_hora = anac_2025[anac_2025["aeropuerto"].isin(top10)].groupby(["aeropuerto", "hora"]).size()
por_hora = (por_hora / dias_2025).unstack("hora", fill_value=0)
por_hora = por_hora.reindex(columns=range(24), fill_value=0)   # las 24 horas, aunque alguna no tenga vuelos
por_hora = por_hora.loc[top10]                                  # ordenados de más a menos vuelos
por_hora.index = [nombre_aeropuerto(c) for c in por_hora.index]

hora_pico = pd.DataFrame({
    "hora_pico": por_hora.idxmax(axis=1),
    "vuelos_en_hora_pico": por_hora.max(axis=1).round(1),
    "vuelos_por_dia": por_hora.sum(axis=1).round(1),
})
print("\n=== Hora pico por aeropuerto (2025, hora argentina) ===")
print(hora_pico)
# Conclusión parcial: Aeroparque es el gran cuello de botella del país:
# 257 vuelos de cabotaje por día y entre 13 y 16,5 por hora desde las 9 hasta
# las 20 (un vuelo cada 4 minutos en la hora pico). Ahí es difícil sumar
# frecuencias en horario central. Ezeiza, en cambio, tiene picos chicos
# (5 vuelos/hora a las 7 y a las 20): tiene lugar para absorber vuelos nuevos.
# En el interior los vuelos se amontonan a la mañana: Bariloche, Iguazú,
# Salta y Ushuaia tienen su pico entre las 8 y las 11.


# ------------------------------------------------------------
# 5.5 GRÁFICOS DE AEROPUERTOS
# ------------------------------------------------------------
FUENTE_DATOS = ("Fuente: ANAC - Aterrizajes y despegues procesados (datos.gob.ar) / "
                "Secretaría de Turismo (datos.yvera.gob.ar)")

# Gráfico 6: pasajeros por vuelo, 15 aeropuertos con más pasajeros por vuelo.
# En azul marino los que además tienen LF alto en Turismo (candidatos).
top_ppv = por_aeropuerto.head(15).sort_values("pax_por_vuelo")
lf_alto = top_ppv["load_factor"] >= LF_ALTO
colores = [AZUL_MARINO if alto else CELESTE for alto in lf_alto]

fig, ax = plt.subplots(figsize=(10, 7))
ax.barh(top_ppv["nombre"], top_ppv["pax_por_vuelo"], color=colores, height=0.65)
for y, ppv, lf in zip(top_ppv["nombre"], top_ppv["pax_por_vuelo"], top_ppv["load_factor"]):
    texto = f"{ppv:.0f}" if pd.isna(lf) else f"{ppv:.0f}  (LF {lf:.1f}%)".replace(".", ",")
    ax.text(ppv + 1, y, texto, va="center", fontsize=9)

# Leyenda armada a mano (con "Patch"), porque las barras usan dos colores.
# Va arriba del gráfico para no tapar ninguna barra.
ax.legend(handles=[Patch(color=AZUL_MARINO, label=f"Load Factor ≥ {LF_ALTO}% (candidatos)"),
                   Patch(color=CELESTE, label=f"Load Factor < {LF_ALTO}%")],
          loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False)

ax.set_xlim(0, top_ppv["pax_por_vuelo"].max() * 1.25)
ax.set_title("Los destinos turísticos reciben los vuelos más cargados (2025)",
             fontsize=13, fontweight="bold", color=AZUL_MARINO, loc="left", pad=32)
ax.set_xlabel("Pasajeros promedio por vuelo (aterrizajes + despegues)")
ax.grid(axis="y", visible=False)
guardar_grafico(fig, "06_pasajeros_por_vuelo_aeropuertos.png")


# Gráfico 7: mapa de calor de vuelos por hora (cuellos de botella).
# Mostramos qué % de los vuelos del día cae en cada hora. Si usáramos la
# cantidad de vuelos, Aeroparque (257 por día) taparía a todos los demás y
# no se vería la hora pico de cada aeropuerto.
porcentaje_hora = por_hora.div(por_hora.sum(axis=1), axis=0) * 100

# Escala de un solo color, de celeste muy claro (pocos vuelos) a azul marino (muchos).
escala_ofca = LinearSegmentedColormap.from_list("ofca", ["#E7F2F7", CELESTE, AZUL_MARINO])

fig, ax = plt.subplots(figsize=(12, 5.5))
imagen = ax.imshow(porcentaje_hora, aspect="auto", cmap=escala_ofca)

# Escribimos el valor solo en la hora pico de cada aeropuerto
for fila, aeropuerto in enumerate(porcentaje_hora.index):
    hora_max = porcentaje_hora.loc[aeropuerto].idxmax()
    valor = porcentaje_hora.loc[aeropuerto, hora_max]
    ax.text(hora_max, fila, f"{valor:.0f}%", ha="center", va="center",
            fontsize=8, color="white", fontweight="bold")
ax.set_xticks(range(24))
ax.set_xticklabels([f"{h}h" for h in range(24)], fontsize=8)
ax.set_yticks(range(len(por_hora)))
ax.set_yticklabels(por_hora.index)
ax.grid(False)   # en un mapa de calor la grilla tapa los colores
for borde in ["left", "bottom"]:
    ax.spines[borde].set_visible(False)

barra = fig.colorbar(imagen, ax=ax)
barra.set_label("% de los vuelos del día")
barra.outline.set_visible(False)

ax.set_title("¿A qué hora se congestionan los aeropuertos? % de vuelos del día por hora (2025)",
             fontsize=13, fontweight="bold", color=AZUL_MARINO, loc="left")
ax.set_xlabel("Hora del día (hora argentina)")
guardar_grafico(fig, "07_vuelos_por_hora_aeropuertos.png")
