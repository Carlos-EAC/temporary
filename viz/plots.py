"""Gráficas y tabla comparativa a partir de trace.json.  [Joel]

Solo lee el log: usa `harvest_sim.telemetria` (reconstruir, series_temporales y calcular_metricas),
nunca la simulación. Guarda PNG en <carpeta del trace>/plots/ y una tabla resumen (CSV y Markdown).

Uso:
    python viz/plots.py runs/escenario_a/trace.json
    python viz/plots.py runs/escenario_a/trace.json runs/escenario_b/trace.json runs/escenario_c/trace.json

Gráficas de cada corrida, agrupadas por la pregunta que responden:
  1. Carga de la cosechadora en el tiempo (diente de sierra).         ¿Cómo se llena y se vacía?
  2. Línea de tiempo de estados de ambos agentes (tipo Gantt).        ¿Qué hace cada agente en cada momento?
  3. Tiempo ocioso acumulado de la cosechadora.                      ¿Cuánto ha esperado hasta ahora?
  4. Distancia entre la cosechadora y el carro, por tick.             ¿Qué tan lejos está el carro?
  5. Grano cosechado y grano en la bodega, contra el total esperado.  ¿Cuánto grano llega?
Y entre escenarios:
  6. Comparación de las métricas principales.
  + tabla resumen (resumen.csv con todas las métricas y resumen.md con las principales).

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

from harvest_sim.telemetria import (  # noqa: E402
    aplanar_metricas,
    calcular_metricas,
    cargar_trace,
    reconstruir,
    series_temporales,
)

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

# Panel de la comparación: (métrica, título del panel). Cada una con su propia escala.
METRICAS_COMPARACION = [
    ("tiempo_completacion", "Tiempo de completación\n(ticks)"),
    ("tick_fin_cosecha", "Fin de la cosecha\n(tick)"),
    ("tiempo_ocioso_cosechadora", "Tiempo ocioso\n(ticks)"),
    ("porcentaje_ocioso", "Tiempo ocioso\n(% del tiempo total)"),
    ("distancia_total", "Distancia total\n(celdas)"),
    ("distancia_cosechadora_carro_promedio", "Distancia media\ncosechadora–carro (celdas)"),
    ("utilizacion_carro", "Utilización del carro\n(fracción del tiempo)"),
    ("porcentaje_entregado", "Grano entregado\n(% del esperado)"),
]
# Columnas de la tabla en Markdown (el CSV lleva todas las métricas)
COLUMNAS_MD = [
    ("escenario", "Escenario"),
    ("tiempo_completacion", "Tiempo de completación"),
    ("tick_fin_cosecha", "Fin de la cosecha"),
    ("tiempo_ocioso_cosechadora", "Tiempo ocioso"),
    ("porcentaje_ocioso", "% ocioso"),
    ("distancia_total", "Distancia total"),
    ("distancia_cosechadora_carro_promedio", "Distancia media cosechadora–carro"),
    ("utilizacion_carro", "Utilización del carro"),
    ("colisiones", "Colisiones"),
    ("ticks_bloqueados", "Ticks bloqueados"),
    ("num_ciclos", "Ciclos"),
    ("grano_total_entregado", "Grano entregado"),
    ("porcentaje_entregado", "% entregado"),
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


def _formato(valor):
    return "—" if valor is None else f"{valor:g}"


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


# --- 3. Tiempo ocioso acumulado -----------------------------------------------------------------
def grafica_ocioso_acumulado(trace, destino, ruta=None):
    """Curva continua: plana mientras la cosechadora trabaja y con pendiente 1 mientras espera al carro.
    Cada punto marca el fin de una espera y su valor es el total acumulado hasta ese momento."""
    _estilo()
    s = series_temporales(trace)
    ticks, acumulado = s["tick"], s["ocioso_acumulado"]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(ticks, acumulado, color=NARANJA, linewidth=2, solid_capstyle="round", solid_joinstyle="round", zorder=3)
    finales = [t for t in ticks if t > 0 and acumulado[t] > acumulado[t - 1]
               and (t == ticks[-1] or acumulado[t + 1] == acumulado[t])]
    ax.plot(finales, [acumulado[t] for t in finales], linestyle="none", marker="o", markersize=8,
            color=NARANJA, markeredgecolor=SUPERFICIE, markeredgewidth=2, zorder=4)
    for t in finales:
        ax.annotate(str(acumulado[t]), (t, acumulado[t]), xytext=(0, 9), textcoords="offset points",
                    ha="center", color=TINTA_2, fontsize=9)
    ax.set_title(f"Tiempo ocioso acumulado de la cosechadora — {nombre_escenario(trace, ruta)}")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Ticks acumulados esperando al carro")
    ax.set_xlim(0, ticks[-1])
    ax.set_ylim(0, max(acumulado + [1]) * 1.18)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    return _guardar(fig, destino)


# --- 4. Distancia entre la cosechadora y el carro, por tick --------------------------------------
def grafica_distancia(trace, destino, ruta=None):
    _estilo()
    s = series_temporales(trace)
    ticks, distancia = s["tick"], s["distancia_cosechadora_carro"]
    promedio = sum(distancia) / len(distancia)
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.axhline(promedio, color=TINTA_TENUE, linewidth=1, zorder=1)
    ax.text(0.99, 0.96, f"línea gris: promedio ({promedio:.1f} celdas)", transform=ax.transAxes, ha="right",
            va="top", color=TINTA_2, fontsize=9)
    ax.step(ticks, distancia, where="post", color=AZUL, linewidth=2, solid_capstyle="round", solid_joinstyle="round", zorder=3)
    ax.set_title(f"Distancia entre la cosechadora y el carro — {nombre_escenario(trace, ruta)}")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Distancia (celdas, Manhattan)")
    ax.set_xlim(0, ticks[-1])
    ax.set_ylim(0, max(distancia + [1]) * 1.15)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    return _guardar(fig, destino)


# --- 5. Grano cosechado y grano en la bodega -----------------------------------------------------
def grafica_grano(trace, destino, ruta=None):
    _estilo()
    s = series_temporales(trace)
    ticks = s["tick"]
    mundo = trace["mundo"]
    esperado = mundo["ancho"] * (mundo["alto"] - 1) * mundo.get("grano_por_celda", 1) if "ancho" in mundo else None
    fig, ax = plt.subplots(figsize=(10, 4.2))
    if esperado:
        ax.axhline(esperado, color=TINTA_TENUE, linewidth=1, zorder=1)
        ax.text(ticks[-1], esperado, f"total esperado ({esperado})", ha="right", va="bottom", color=TINTA_2, fontsize=9)
    ax.step(ticks, s["cosechado_acumulado"], where="post", color=AQUA, linewidth=2, solid_capstyle="round", zorder=3,
            label="Cosechado acumulado")
    ax.step(ticks, s["entregado_en_bodega"], where="post", color=AZUL, linewidth=2, solid_capstyle="round", zorder=4,
            label="En la bodega")
    ax.set_title(f"Grano cosechado y grano en la bodega — {nombre_escenario(trace, ruta)}")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Unidades de grano")
    ax.set_xlim(0, ticks[-1])
    ax.set_ylim(0, (esperado or max(s["cosechado_acumulado"] + [1])) * 1.15)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.86))  # debajo de la línea del total esperado
    return _guardar(fig, destino)


# --- 6. Comparación entre escenarios ------------------------------------------------------------
def grafica_comparacion(traces, destino):
    """`traces`: {nombre: trace}. Un panel por métrica (cada una con su propia escala) y un color fijo por escenario."""
    if len(traces) > len(SERIES):
        raise ValueError(f"se pueden comparar hasta {len(SERIES)} escenarios a la vez")
    _estilo()
    metricas = {nombre: calcular_metricas(t) for nombre, t in traces.items()}
    nombres = list(traces)
    columnas = 4
    filas = -(-len(METRICAS_COMPARACION) // columnas)
    fig, ejes = plt.subplots(filas, columnas, figsize=(13, 4.0 * filas))
    for ax, (clave, titulo) in zip(ejes.flat, METRICAS_COMPARACION):
        valores = [metricas[n][clave] or 0 for n in nombres]
        barras = ax.bar(range(len(nombres)), valores, width=0.55, color=SERIES[:len(nombres)],
                        edgecolor=SUPERFICIE, linewidth=1.5)
        for barra, valor in zip(barras, valores):
            ax.text(barra.get_x() + barra.get_width() / 2, valor, _formato(valor), ha="center", va="bottom",
                    color=TINTA_2, fontsize=9)
        ax.set_title(titulo, fontsize=10)
        ax.set_xticks(range(len(nombres)))
        ax.set_xticklabels([n.replace("escenario_", "").upper() if n.startswith("escenario_") else n
                            for n in nombres], fontsize=9)
        ax.grid(axis="x", visible=False)
        ax.set_xlim(-0.7, max(len(nombres), 3) - 1 + 0.7)
        ax.set_ylim(0, max(valores + [1]) * 1.18)
    for ax in list(ejes.flat)[len(METRICAS_COMPARACION):]:
        ax.set_visible(False)
    if len(nombres) > 1:
        asas = [Patch(facecolor=SERIES[i], edgecolor=SUPERFICIE, label=n) for i, n in enumerate(nombres)]
        fig.legend(handles=asas, loc="lower center", ncol=len(asas))
    fig.suptitle("Comparación entre escenarios (línea base)", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout(rect=(0, 0.05 if len(nombres) > 1 else 0, 1, 0.96))
    return _guardar(fig, destino)


# --- Tabla resumen ------------------------------------------------------------------------------
def tabla_resumen(traces, destino_csv, destino_md):
    """Una fila por escenario. El CSV lleva TODAS las métricas (anidadas aplanadas con '.'); el Markdown, las principales."""
    metricas = {nombre: calcular_metricas(t) for nombre, t in traces.items()}
    destino_csv, destino_md = Path(destino_csv), Path(destino_md)
    destino_csv.parent.mkdir(parents=True, exist_ok=True)

    filas = {nombre: {"escenario": nombre, **aplanar_metricas(m)} for nombre, m in metricas.items()}
    columnas = []
    for fila in filas.values():
        columnas += [c for c in fila if c not in columnas]  # unión, en orden de aparición
    with open(destino_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(columnas)
        for fila in filas.values():
            w.writerow(["" if fila.get(c) is None else fila.get(c, "") for c in columnas])

    def valor_md(nombre, clave):
        v = metricas[nombre].get(clave) if clave != "escenario" else nombre
        return str(sum(v.values())) if isinstance(v, dict) else _formato(v) if not isinstance(v, str) else v

    lineas = ["| " + " | ".join(t for _, t in COLUMNAS_MD) + " |", "|" + "---|" * len(COLUMNAS_MD)]
    for nombre in metricas:
        lineas.append("| " + " | ".join(valor_md(nombre, k) for k, _ in COLUMNAS_MD) + " |")
    destino_md.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return destino_csv, destino_md


# --- Orquestación -------------------------------------------------------------------------------
def graficas_de_un_trace(ruta_trace, carpeta=None):
    """Las gráficas 1 a 5 de un trace.json. Devuelve las rutas generadas."""
    trace = cargar_trace(ruta_trace)
    carpeta = Path(carpeta) if carpeta else Path(ruta_trace).resolve().parent / "plots"
    return [
        grafica_carga(trace, carpeta / "1_carga_cosechadora.png", ruta_trace),
        grafica_estados(trace, carpeta / "2_linea_de_tiempo_estados.png", ruta_trace),
        grafica_ocioso_acumulado(trace, carpeta / "3_ocioso_acumulado.png", ruta_trace),
        grafica_distancia(trace, carpeta / "4_distancia_cosechadora_carro.png", ruta_trace),
        grafica_grano(trace, carpeta / "5_grano_en_bodega.png", ruta_trace),
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Genera las gráficas y la tabla resumen a partir de trace.json.")
    parser.add_argument("trace", nargs="+", help="uno o más trace.json (la gráfica 6 y la tabla comparan varios)")
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
    generados.append(grafica_comparacion(traces, comparacion / "6_comparacion_escenarios.png"))
    generados += tabla_resumen(traces, comparacion / "resumen.csv", comparacion / "resumen.md")
    for g in generados:
        print(g)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
