# CLAUDE.md — TPO OFCA (Grupo 10)

Contexto para Claude Code. Leer completo antes de tocar código.

## Qué es este proyecto

Trabajo Práctico Obligatorio (TPO) de **Taller de Programación II — UADE**.
Grupo 10: Luciana Pirruccio, Agostina Pacheco, Sebastián Gómez Martínez. Profesora: María Julia Monasterio.

Marca ficticia del proyecto: **OFCA — Observatorio Federal de Conectividad Aérea** (Secretaría de Turismo, República Argentina).
Eslogan: *"Todo el país, más cerca"*.

**Tema:** análisis estadístico de la demanda histórica y del factor de ocupación (Load Factor) en las rutas aéreas de **cabotaje** de Argentina, para identificar cuellos de botella operativos y evaluar la viabilidad de sumar frecuencias en ciertas rutas o aeropuertos.

**Período:** 2020 a 2026 (2026 llega hasta julio).

## Quiénes trabajan acá

Son estudiantes que están aprendiendo Python, pandas y matplotlib. Por eso:

- **Código simple y didáctico.** Nada de clases, decoradores, type hints complejos ni abstracciones innecesarias. Funciones cortas, nombres claros.
- **Comentarios en español** que expliquen el *porqué* de cada paso (la consigna los evalúa).
- **Explicar cada cambio** en la respuesta: qué se hizo y por qué, en lenguaje simple.
- **Ante una decisión de análisis dudosa, preguntar antes** de implementarla.
- Todo en **español** (código, comentarios, nombres de variables, mensajes por consola).

## Requisitos de la consigna (no romper)

- Datos reales de una fuente abierta, **con link a la fuente original en el código**.
- Proceso visible de **extracción** (con `requests`), **validación y limpieza**.
- Análisis con **pandas**: métricas/KPIs (promedios, rankings, evoluciones temporales, etc.).
- Gráficos con **matplotlib** (seaborn/plotly opcionales), claros y con la identidad visual de OFCA.
- **Conclusiones parciales** comentadas en el código, explicando los hallazgos.
- Entrega final en un .zip `TPI_TallerProgII_G10.zip` con: el **.py**, el **dataset** (.csv), la presentación, un .txt con legajos y nombres, y material extra (logo, guía de estilo).
  → El entregable de código es **un solo archivo `.py`**: mantener todo en `tpo_ofca.py` salvo que el grupo decida otra cosa.

## Cómo correr

```bash
pip install -r requirements.txt
python tpo_ofca.py
```

La primera vez descarga el CSV (~270 MB) a `data/`. Después lo reutiliza.

## Fuentes de datos

### 1. Secretaría de Turismo — Conectividad Aérea (EN USO)
- Dataset: https://datos.yvera.gob.ar/dataset/conectividad-aerea
- Archivo: `base_microdatos.csv` ("Base agregada de frecuencias aéreas")
  https://datos.yvera.gob.ar/dataset/c0e7bc3d-553c-405c-8b32-79282b28ffd5/resource/aab49234-28c9-48ab-a978-a83485139290/download/base_microdatos.csv
- Origen real de los datos: SIAC de la **ANAC**, procesado por la Dirección de Mercados y Estadísticas de Turismo.
- Un solo CSV con todos los años (2017-01-01 → 2026-07-31), **1.078.289 filas, 19 columnas**, separador `,`, UTF-8.
- Columnas: `indice_tiempo` (fecha diaria), `clasificacion_vuelo` (Cabotaje / Internacional), `clase_vuelo` (Regular / No Regular), `aerolinea`, `origen_oaci`, `origen_aeropuerto`, `origen_localidad`, `origen_provincia`, `origen_pais`, `origen_continente`, `destino_oaci`, `destino_aeropuerto`, `destino_localidad`, `destino_provincia`, `destino_pais`, `destino_continente`, `pasajeros`, `asientos`, `vuelos`.
- **Por qué esta y no la de ANAC:** es la única que trae `asientos`, necesarios para el Load Factor.
- Advertencia: Turismo filtró vuelos desde/hacia aeropuertos "sin relevancia turística" (ver `novedades.csv` del dataset). Algunos aeropuertos chicos pueden faltar. Mencionarlo en el informe.

### 2. ANAC — Aterrizajes y despegues procesados (PENDIENTE, decisión abierta)
- https://datos.gob.ar/dataset/aterrizajes-y-despegues-procesados-por-la-administracion-nacional-de-aviacion-civil-anac
- Un CSV por año (2019 a 2026). Trae **hora** y aeropuerto de cada movimiento, pasajeros, aeronave, aerolínea. **No trae asientos.**
- Uso posible: horarios pico por aeropuerto (cuellos de botella operativos), que la base de Turismo no permite (solo tiene fecha).
- Cuidados si se usa: probablemente separador `;` y posible encoding `latin-1`; **cada vuelo de cabotaje aparece dos veces** (despegue en origen + aterrizaje en destino), así que para totales hay que filtrar un solo tipo de movimiento; los nombres de columnas pueden variar entre años (verificar `df.columns` de cada archivo antes de concatenar).
- Los links de datos.gob.ar apuntan a la página del recurso; la URL de descarga directa está en el botón "Descargar" de cada año (la de 2026 es `https://datos.transporte.gob.ar/dataset/21038a1a-c3c7-4494-b76a-3a2a8fbb83b5/resource/7b6d0103-0a69-4c67-aed9-33cb58ae12f5/download/202608-informe-ministerio_modificado.csv`).

## Decisiones de limpieza ya tomadas

1. Período: `anio >= 2020`.
2. Solo `clasificacion_vuelo == "Cabotaje"` (vuelos dentro de Argentina).
3. Solo `clase_vuelo == "Regular"`: los no regulares (chárter) distorsionan la demanda normal de una ruta.
4. Validación: se descartan filas con nulos, `asientos == 0` o `pasajeros > asientos` (en la práctica hubo 0 casos; la base viene prolija).
5. Columnas auxiliares: `anio`, `mes`, `ruta = origen_localidad + " - " + destino_localidad`.
   La ruta **tiene sentido** (A–B ≠ B–A). Es intencional: un sentido puede ir más lleno que el otro.
6. Resultado: **370.950 filas**. Se guarda en `data/cabotaje_limpio_2020_2026.csv`.

## Definición de KPIs

- **Load Factor (LF) = Σ pasajeros / Σ asientos × 100.**
  Siempre **sumar primero y dividir después** dentro de cada grupo. Nunca promediar LFs de filas (pondera igual una ruta chica que Aeroparque–Córdoba).
- Rankings por ruta/aeropuerto: filtrar un mínimo de volumen (hoy `vuelos >= 300` en el año) para no sacar conclusiones de rutas con pocos vuelos.
- Comparaciones interanuales que incluyan 2026: usar **enero–julio de cada año**, porque 2026 está incompleto y tiene estacionalidad (verano + vacaciones de invierno).
- Referencia de interpretación: LF ≥ ~88% sostenido + mucho volumen = candidata a sumar frecuencias; LF < ~75% = sobreoferta.

## Hallazgos hasta ahora (para conclusiones parciales)

- Pasajeros de cabotaje regular: 3,6 M (2020) → 6,0 M (2021) → 13,4 M (2022) → 17,2 M (2023) → 15,7 M (2024) → 17,2 M (2025) → 9,2 M (2026 ene–jul).
- LF anual: 80,3% (2020), 81,8% (2021), 86,0% (2022), 85,9% (2023), 85,0% (2024), 84,5% (2025), 86,2% (2026 ene–jul).
- Ene–jul: 2026 tiene 5,5% menos pasajeros que 2025, pero LF más alto (86,2% vs 83,9%) → se ofrecieron menos asientos y van más llenos.
- Estacionalidad del LF: picos en noviembre (87,6%), octubre, febrero; mínimos abril–mayo (~82,6%).
- Rutas con mayor LF en 2025 (≥300 vuelos): El Calafate → CABA 89,4%, CABA → Salta 88,8%, CABA → El Calafate 88,4%, CABA → Puerto Iguazú 88,2%, CABA → Tucumán 88,1%, Bariloche → CABA 88,1%, también Ushuaia, Neuquén, Jujuy (~88%). Casi todas son **destinos turísticos conectados a Aeroparque**.
- Rutas con más pasajeros en 2025: CABA ↔ Córdoba (~730 mil por sentido), CABA ↔ Mendoza, CABA ↔ Bariloche, CABA ↔ Iguazú.
- Nota: en la base, "Ciudad de Buenos Aires" = Aeroparque y "Ezeiza" aparece aparte. Considerar unificarlos como "Buenos Aires" si se analiza por ciudad.

## Identidad visual (usar en todos los gráficos)

Paleta oficial (de la guía de estilo):

| Uso sugerido | Hex |
|---|---|
| Amarillo (acento, destacar un valor) | `#F2D565` |
| Celeste (serie principal) | `#7BB6D1` |
| Gris azulado (series secundarias, grillas) | `#93AAB5` |
| Gris oscuro (texto, ejes) | `#272F33` |

Colores del logo (complementarios): azul marino `#14284B` (títulos, serie fuerte), azul acero `#527D9B`, celeste muy claro `#E7F2F7` (fondos).

Tipografía: **Montserrat** (principal, títulos) y **Encode Sans** (secundaria). En matplotlib usarlas si están instaladas; si no, caer a una sans-serif sin romper el script.

Criterios de gráficos: título claro que diga la conclusión, ejes con unidades, sin bordes superiores/derechos, fuente citada abajo ("Fuente: ANAC / Secretaría de Turismo"). Guardar en `graficos/` como PNG (dpi 150+) para usar en la presentación.

## Estructura del repo

```
tpo_ofca.py            # script principal (único entregable de código)
requirements.txt
data/                  # CSVs (ignorado por git, ver abajo)
graficos/              # PNGs generados por el script
docs/                  # consigna, guía de estilo, logo
```

## Cuidados

- **`data/` está en `.gitignore`**: `base_microdatos.csv` pesa ~270 MB y GitHub rechaza archivos > 100 MB. El script lo descarga solo.
- El CSV limpio también puede ser pesado para el .zip; si hace falta, entregar una versión agregada (por ruta/mes) en lugar del detalle diario.
- Rutas de archivos siempre relativas a la carpeta del script (`BASE` con `__file__`, fallback a `os.getcwd()`). Nunca rutas absolutas de una compu en particular.
- No cambiar la definición de LF ni los filtros sin avisar: los números ya están en el informe.

## Próximos pasos

1. Decidir si se suma la base de ANAC (horarios pico por aeropuerto) o se trabaja solo con Turismo.
2. Gráficos con matplotlib: evolución anual de pasajeros y LF, estacionalidad mensual, ranking de rutas por LF, matriz volumen vs LF (para detectar rutas candidatas a más frecuencias).
3. KPIs finales y conclusiones de negocio.
4. Armar el .zip de entrega.
