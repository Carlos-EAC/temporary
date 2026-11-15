"""Gráficas y tabla comparativa a partir de trace.json.  [Joel]

Especificación §7.2. Solo lee el log: usa `harvest_sim.telemetria` (reconstruir y calcular_metricas),
nunca la simulación. Guarda PNG en runs/<escenario>/plots/ y una tabla resumen (CSV y Markdown).

Uso:
    python viz/plots.py runs/escenario_a/trace.json
    python viz/plots.py runs/escenario_a/trace.json runs/escenario_b/trace.json runs/escenario_c/trace.json

Gráficas:
  1. Carga de la cosechadora vs. tiempo (diente de sierra).
  2. Línea de tiempo de estados de ambos agentes (tipo Gantt).
  3. Tiempo ocioso por ciclo.
  4. Comparación entre escenarios (tiempo ocioso, fin de la cosecha, completación y distancia total).

Diseño (guía de visualización): paleta categórica validada con 6 hues en orden fijo, texto en tintas de
texto (nunca en el color de la serie), marcas delgadas con un hueco del color de la superficie entre
ellas, leyenda cuando hay 2 o más series y etiquetas directas donde caben. Los 11 estados de los agentes
se agrupan en 7 categorías de actividad para no pasar de la paleta validada.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin ventana: funciona en servidores y en CI
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from harvest_sim.telemetria import calcular_metricas, cargar_trace, reconstruir  # noqa: E402

# --- Tokens de la paleta de referencia (modo claro) ---------------------------------------------
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_TENUE = "#898781"
REJILLA = "#e1e0d9"
EJE = "#c3c2b7"
AZUL, NARANJA, AQUA, AMARILLO, MAGENTA, VERDE = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"
# Orden fijo de los hues categóricos (el orden validado): azul, naranja, aqua, amarillo, magenta, verde
SERIES = [AZUL, NARANJA, AQUA, AMARILLO, MAGENTA, VERDE]

# Categorías de actividad: (clave, etiqueta de la leyenda, color, estados). El color sigue a la categoría.
CATEGORIAS = [
    ("desplazamiento", "Desplazamiento", AZUL,
     {"YENDO_A_CAMPO", "YENDO_A_COSECHADORA", "YENDO_A_BODEGA", "REGRESANDO_A_BASE"}),
    ("ocioso", "Cosechadora llena esperando al carro (ocioso)", NARANJA, {"LLENA_ESPERANDO"}),
    ("cosecha", "Cosechando", AQUA, {"COSECHANDO"}),
    ("espera_carro", "Carro esperando la transferencia", AMARILLO, {"ESPERANDO_TRANSFERENCIA"}),
    ("transferencia", "Transfiriendo", MAGENTA, {"TRANSFIRIENDO"}),
    ("descarga", "Descargando en la bodega", VERDE, {"DESCARGANDO"}),
    ("reposo", "En base o terminado", EJE, {"EN_BASE", "FIN"}),
]
OTROS = ("otros", "Otros estados", TINTA_TENUE)
CATEGORIA_DE_ESTADO = {estado: (clave, etiqueta, color) for clave, etiqueta, color, estados in CATEGORIAS for estado in estados}

METRICAS_COMPARACION = [
    ("tiempo_ocioso_cosechadora", "Tiempo ocioso\n(ticks)"),
    ("tick_fin_cosecha", "Fin de la cosecha\n(tick)"),
    ("tiempo_completacion", "Tiempo de completación\n(ticks)"),
    ("distancia_total", "Distancia total\n(celdas)"),
]
COLUMNAS_TABLA = [
    ("escenario", "Escenario"),
    ("tiempo_ocioso_cosechadora", "Tiempo ocioso"),
    ("tiempo_transfiriendo", "Tiempo transfiriendo"),
    ("tick_fin_cosecha", "Fin de la cosecha"),
    ("tiempo_completacion", "Tiempo de completación"),
    ("distancia_cosechadora", "Distancia cosechadora"),
    ("distancia_carro", "Distancia carro"),
    ("distancia_total", "Distancia total"),
    ("colisiones", "Colisiones"),
    ("ticks_bloqueados", "Ticks bloqueados"),
    ("num_ciclos", "Ciclos"),
    ("utilizacion_carro", "Utilización del carro"),
    ("grano_total_entregado", "Grano entregado"),
]


def _estilo():
    plt.rcParams.update({
        "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE, "savefig.facecolor": SUPERFICIE,
        "axes.edgecolor": EJE, "axes.labelcolor": TINTA_2, "axes.titlecolor": TINTA,
        "xtick.color": TINTA_2, "ytick.color": TINTA_2, "text.color": TINTA,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": REJILLA, "grid.linewidth": 1, "grid.linestyle": "-",
        "axes.axisbelow": True, "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "legend.frameon": False, "legend.fontsize": 9,
    })


def nombre_escenario(trace, ruta=None):
    return trace["meta"].get("escenario") or (Path(ruta).resolve().parent.name if ruta else "escenario")


def _guardar(fig, destino):
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, dpi=150, bbox_inches="tight", pad_inches=0.25, metadata={"Software": None})
    plt.close(fig)
    return destino


def _cosechadora(trace):
    return next(a for a in trace["agentes"] if a["tipo"] == "cosechadora")


def _tramos(estados, agente):
    """[(estado, tick_inicial, largo)] con ticks consecutivos del mismo estado."""
    tramos = []
    for e in estados:
        estado = e["agentes"][agente]["estado"]
        if tramos and tramos[-1][0] == estado:
            tramos[-1][2] += 1
        else:
            tramos.append([estado, e["tick"], 1])
    return tramos


def _categoria(estado):
    return CATEGORIA_DE_ESTADO.get(estado, OTROS)


def _color_texto(color):
    return TINTA if color in (AMARILLO, EJE) else "#ffffff"


# --- 1. Carga de la cosechadora vs. tiempo ------------------------------------------------------
def grafica_carga(trace, destino, ruta=None):
    _estilo()
    h = _cosechadora(trace)
    estados = list(reconstruir(trace))
    ticks = [e["tick"] for e in estados]
    carga = [e["agentes"][h["id"]]["carga"] for e in estados]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.axhline(h["capacidad"], color=TINTA_TENUE, linewidth=1, zorder=1)
    ax.step(ticks, carga, where="post", color=AZUL, linewidth=2, solid_capstyle="round", solid_joinstyle="round", zorder=3)
    ax.text(ticks[-1], h["capacidad"], f"capacidad ({h['capacidad']})", ha="right", va="bottom",
            color=TINTA_2, fontsize=9)
    ax.set_title(f"Carga de la cosechadora en el tiempo — {nombre_escenario(trace, ruta)}")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Carga (unidades de grano)")
    ax.set_xlim(0, ticks[-1])
    ax.set_ylim(0, h["capacidad"] * 1.15)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    return _guardar(fig, destino)


# --- 2. Línea de tiempo de estados --------------------------------------------------------------
def grafica_estados(trace, destino, ruta=None):
    _estilo()
    estados = list(reconstruir(trace))
    total = trace["meta"]["total_ticks"] + 1
    agentes = [a["id"] for a in trace["agentes"]]
    ancho_fig = 13
    ticks_por_pulgada = total / (ancho_fig * 0.82)
    fig, ax = plt.subplots(figsize=(ancho_fig, 1.5 + 0.9 * len(agentes)))
    ax.grid(axis="y", visible=False)
    presentes = {}
    for fila, a in enumerate(agentes):
        y = len(agentes) - 1 - fila
        for estado, inicio, largo in _tramos(estados, a):
            clave, etiqueta, color = _categoria(estado)
            presentes.setdefault(clave, (etiqueta, color))
            ax.barh(y, largo, left=inicio, height=0.5, color=color, edgecolor=SUPERFICIE, linewidth=1.5)
            if largo / ticks_por_pulgada >= 0.065 * len(estado) + 0.05:  # el nombre cabe dentro de la barra
                ax.text(inicio + largo / 2, y, estado, ha="center", va="center", fontsize=7,
                        color=_color_texto(color))
    ax.set_yticks(range(len(agentes)))
    ax.set_yticklabels(list(reversed(agentes)))
    ax.set_xlim(0, total)
    ax.set_ylim(-0.6, len(agentes) - 0.4)
    ax.set_xlabel("Tick")
    ax.set_title(f"Línea de tiempo de estados — {nombre_escenario(trace, ruta)}")
    orden = [c for c in CATEGORIAS if c[0] in presentes] + ([OTROS] if "otros" in presentes else [])
    asas = [Patch(facecolor=c[2], edgecolor=SUPERFICIE, label=c[1]) for c in orden]
    ax.legend(handles=asas, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=min(4, len(asas)))
    return _guardar(fig, destino)


# --- 3. Tiempo ocioso por ciclo -----------------------------------------------------------------
def grafica_espera(trace, destino, ruta=None):
    _estilo()
    metricas = calcular_metricas(trace)
    esperas = metricas["espera_por_ciclo"]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.grid(axis="x", visible=False)
    if esperas:
        etiquetas = [f"Ciclo {i}" for i in range(1, len(esperas) + 1)]
        barras = ax.bar(etiquetas, esperas, width=0.5, color=NARANJA, edgecolor=SUPERFICIE, linewidth=1.5)
        for barra, valor in zip(barras, esperas):
            ax.text(barra.get_x() + barra.get_width() / 2, valor, str(valor), ha="center", va="bottom",
                    color=TINTA_2, fontsize=9)
        ax.set_ylim(0, max(esperas) * 1.15)
    else:
        ax.text(0.5, 0.5, "La cosechadora no esperó al carro", ha="center", va="center",
                transform=ax.transAxes, color=TINTA_2)
    ax.set_title(f"Tiempo ocioso por ciclo — {nombre_escenario(trace, ruta)}")
    ax.set_ylabel("Ticks esperando al carro")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.text(0, -0.2, f"Total ocioso: {metricas['tiempo_ocioso_cosechadora']} ticks", transform=ax.transAxes,
            color=TINTA_2, fontsize=9)
    return _guardar(fig, destino)


# --- 4. Comparación entre escenarios ------------------------------------------------------------
def grafica_comparacion(traces, destino):
    """`traces`: {nombre: trace}. Un panel por métrica (cada una con su propia escala) y un color fijo por escenario."""
    if len(traces) > len(SERIES):
        raise ValueError(f"se pueden comparar hasta {len(SERIES)} escenarios a la vez")
    _estilo()
    metricas = {nombre: calcular_metricas(t) for nombre, t in traces.items()}
    nombres = list(traces)
    fig, ejes = plt.subplots(1, len(METRICAS_COMPARACION), figsize=(13, 4.6))
    for ax, (clave, titulo) in zip(ejes, METRICAS_COMPARACION):
        valores = [metricas[n][clave] or 0 for n in nombres]
        barras = ax.bar(range(len(nombres)), valores, width=0.55, color=SERIES[:len(nombres)],
                        edgecolor=SUPERFICIE, linewidth=1.5)
        for barra, valor in zip(barras, valores):
            ax.text(barra.get_x() + barra.get_width() / 2, valor, str(valor), ha="center", va="bottom",
                    color=TINTA_2, fontsize=9)
        ax.set_title(titulo, fontsize=10)
        ax.set_xticks(range(len(nombres)))
        ax.set_xticklabels([n.replace("escenario_", "").upper() if n.startswith("escenario_") else n
                            for n in nombres], fontsize=9)
        ax.grid(axis="x", visible=False)
        ax.set_xlim(-0.7, max(len(nombres), 3) - 1 + 0.7)
        ax.set_ylim(0, max(valores + [1]) * 1.18)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    if len(nombres) > 1:
        asas = [Patch(facecolor=SERIES[i], edgecolor=SUPERFICIE, label=n) for i, n in enumerate(nombres)]
        fig.legend(handles=asas, loc="lower center", ncol=len(asas))
    fig.suptitle("Comparación entre escenarios (línea base)", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout(rect=(0, 0.08 if len(nombres) > 1 else 0, 1, 0.95))
    return _guardar(fig, destino)


# --- Tabla resumen ------------------------------------------------------------------------------
def _fila(nombre, trace):
    m = calcular_metricas(trace)
    return {"escenario": nombre, **{k: m[k] for k, _ in COLUMNAS_TABLA[1:]}, "ticks_bloqueados": sum(m["ticks_bloqueados"].values())}


def tabla_resumen(traces, destino_csv, destino_md):
    """Una fila por escenario y una columna por métrica (CSV y Markdown)."""
    filas = [_fila(nombre, t) for nombre, t in traces.items()]
    destino_csv, destino_md = Path(destino_csv), Path(destino_md)
    destino_csv.parent.mkdir(parents=True, exist_ok=True)
    claves = [k for k, _ in COLUMNAS_TABLA]
    with open(destino_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(claves)
        for fila in filas:
            w.writerow(["" if fila[k] is None else fila[k] for k in claves])
    lineas = ["| " + " | ".join(t for _, t in COLUMNAS_TABLA) + " |", "|" + "---|" * len(COLUMNAS_TABLA)]
    for fila in filas:
        lineas.append("| " + " | ".join("—" if fila[k] is None else str(fila[k]) for k in claves) + " |")
    destino_md.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return destino_csv, destino_md


# --- Orquestación -------------------------------------------------------------------------------
def graficas_de_un_trace(ruta_trace, carpeta=None):
    """Las gráficas 1 a 3 de un trace.json. Devuelve las rutas generadas."""
    trace = cargar_trace(ruta_trace)
    carpeta = Path(carpeta) if carpeta else Path(ruta_trace).resolve().parent / "plots"
    return [
        grafica_carga(trace, carpeta / "1_carga_cosechadora.png", ruta_trace),
        grafica_estados(trace, carpeta / "2_linea_de_tiempo_estados.png", ruta_trace),
        grafica_espera(trace, carpeta / "3_ocio_por_ciclo.png", ruta_trace),
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Genera las gráficas y la tabla resumen a partir de trace.json.")
    parser.add_argument("trace", nargs="+", help="uno o más trace.json (la gráfica 4 y la tabla comparan varios)")
    parser.add_argument("--salida", help="carpeta de salida (por defecto, junto a cada trace y en <runs>/comparacion)")
    args = parser.parse_args(argv)

    traces, generados = {}, []
    for ruta in args.trace:
        trace = cargar_trace(ruta)
        nombre = nombre_escenario(trace, ruta)
        traces[nombre] = trace
        carpeta = Path(args.salida) / nombre if args.salida else None
        generados += graficas_de_un_trace(ruta, carpeta)
    if args.salida:
        comparacion = Path(args.salida) / "comparacion"
    else:
        comparacion = Path(args.trace[0]).resolve().parent.parent / "comparacion"
    generados.append(grafica_comparacion(traces, comparacion / "4_comparacion_escenarios.png"))
    generados += tabla_resumen(traces, comparacion / "resumen.csv", comparacion / "resumen.md")
    for g in generados:
        print(g)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
