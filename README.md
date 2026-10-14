# OFCA — Observatorio Federal de Conectividad Aérea

> *"Todo el país, más cerca"*

Trabajo Práctico Obligatorio de **Taller de Programación II (UADE)** — Grupo 10.

**Integrantes:** Luciana Pirruccio, Agostina Pacheco, Sebastián Gómez Martínez
**Profesora:** María Julia Monasterio

---

## ¿De qué se trata?

Analizamos los vuelos de **cabotaje** (dentro de Argentina) entre **2020 y 2026** para responder una pregunta:

**¿En qué rutas y aeropuertos los aviones van tan llenos que convendría sumar más vuelos?**

Para eso medimos la demanda (cantidad de pasajeros) y el **factor de ocupación** o *Load Factor*: qué porcentaje de los asientos ofrecidos se ocupó.

```
Load Factor = pasajeros / asientos disponibles × 100
```

Un Load Factor alto y sostenido en una ruta con mucho tráfico indica que la demanda supera la oferta: es una candidata a tener más frecuencias.

## Fuentes de datos

| Fuente | Qué usamos | Link |
|---|---|---|
| Secretaría de Turismo — Conectividad Aérea (datos de la ANAC) | Vuelos, pasajeros y asientos por día, ruta y aerolínea | [datos.yvera.gob.ar](https://datos.yvera.gob.ar/dataset/conectividad-aerea) |
| ANAC — Aterrizajes y despegues procesados | Pasajeros por vuelo y horarios pico por aeropuerto (2020–2026) | [datos.gob.ar](https://datos.gob.ar/dataset/aterrizajes-y-despegues-procesados-por-la-administracion-nacional-de-aviacion-civil-anac) |

Los datos son abiertos (licencia CC-BY-4.0).

## Cómo correrlo

Necesitás **Python 3.10 o superior**.

```bash
# 1. Clonar el repo y entrar a la carpeta
git clone <url-del-repo>
cd tpo-ofca

# 2. (Opcional, recomendado) crear un entorno virtual
python3 -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate

# 3. Instalar las librerías
pip install -r requirements.txt

# 4. Ejecutar
python tpo_ofca.py
```

La primera vez, el script **descarga automáticamente** los datos (~270 MB de Turismo + un CSV por año de ANAC) a la carpeta `data/`. Las siguientes veces usa el archivo ya descargado.

> **Mac y error de certificados SSL** (`CERTIFICATE_VERIFY_FAILED`): si instalaste Python desde python.org, ejecutá una vez *Aplicaciones → Python 3.x → Install Certificates.command*.

## Qué hace el script

1. **Extracción:** descarga el CSV con `requests`.
2. **Validación y limpieza:** se queda con vuelos de cabotaje regulares desde 2020, revisa nulos y datos inconsistentes.
3. **Análisis (pandas):** Load Factor por año, por mes, por ruta y por aeropuerto; comparación enero–julio entre años.
4. **Visualización (matplotlib):** gráficos con la identidad visual de OFCA, guardados en `graficos/`.
5. **Conclusiones:** comentadas en el código y desarrolladas en la presentación.

## Primeros hallazgos

- La demanda se **cuadruplicó** después de la pandemia: de 3,6 millones de pasajeros en 2020 a más de 17 millones en 2023 y 2025.
- El Load Factor de cabotaje se mantiene **alto, entre 84% y 86%** desde 2022.
- Las rutas más llenas son **destinos turísticos conectados con Aeroparque**: El Calafate, Salta, Puerto Iguazú, Tucumán, Bariloche y Ushuaia, todas por encima del 88%.

## Estructura del proyecto

```
tpo-ofca/
├── tpo_ofca.py          # código principal
├── requirements.txt     # librerías necesarias
├── data/                # datos descargados (no se suben al repo)
├── graficos/            # gráficos generados
└── docs/                # consigna, guía de estilo y logo
```

## Identidad visual

- **Paleta:** `#F2D565` · `#7BB6D1` · `#93AAB5` · `#272F33`
- **Tipografías:** Montserrat (principal) y Encode Sans (secundaria)
