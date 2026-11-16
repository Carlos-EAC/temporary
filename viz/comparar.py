"""Comparación de una corrida nueva contra la línea base (tarea 8 de Datos).  [Joel]

El objetivo del reto es reducir el tiempo ocioso frente a la línea base, en los mismos mapas y seeds.
Este script toma la línea base y la corrida nueva de cada escenario y dice, métrica por métrica, qué
cambió y si es una mejora: "mejor" es lo que aprovecha mejor los recursos, sobre todo el tiempo
(el sentido de cada métrica está en harvest_sim.telemetria.SENTIDO_METRICAS).

Uso:
    # un escenario: dos archivos
    python viz/comparar.py runs/linea_base/escenario_a/trace.json runs/mejora/escenario_a/trace.json
    # varios escenarios: dos carpetas con <escenario>/trace.json (se emparejan por nombre)
    python viz/comparar.py runs/linea_base runs/mejora --salida runs/comparacion_linea_base

Genera:
    mejora_vs_linea_base.png   antes y después de las métricas principales (un panel por métrica)
    cambios.csv                todas las métricas: escenario, métrica, base, nueva, diferencia, %, sentido, resultado
    cambios.md                 las métricas principales, para el reporte
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(AQUI))

import plots  # noqa: E402  (tokens de la paleta, estilo y métricas principales)
from harvest_sim.telemetria import cargar_parametros, cargar_trace, comparar_corridas  # noqa: E402

# Antes y después de una misma cosa: un solo hue en dos tonos (claro = línea base, oscuro = nueva).
COLOR_BASE = "#86b6ef"
COLOR_NUEVA = "#1c5cab"
NOTA_SENTIDO = {"menor": "menor es mejor", "mayor": "mayor es mejor", "neutro": "informativa"}
SALIDA_POR_DEFECTO = RAIZ / "runs" / "comparacion_linea_base"
COLUMNAS_CSV = ["escenario", "metrica", "base", "nueva", "diferencia", "cambio_pct", "sentido", "resultado"]


def emparejar(base, nueva):
    """[(escenario, ruta_base, ruta_nueva)] a partir de dos archivos o de dos carpetas.
    Devuelve también los escenarios de la base que no tienen corrida nueva."""
    base, nueva = Path(base), Path(nueva)
    if base.is_file() and nueva.is_file():
        nombre = cargar_trace(base)["meta"].get("escenario") or base.parent.name
        return [(nombre, base, nueva)], []
    if base.is_dir() and nueva.is_dir():
        pares, sin_pareja = [], []
        for ruta in sorted(base.glob("*/trace.json")):
            otra = nueva / ruta.parent.name / "trace.json"
            (pares.append((ruta.parent.name, ruta, otra)) if otra.exists() else sin_pareja.append(ruta.parent.name))
        return pares, sin_pareja
    raise ValueError("base y nueva deben ser ambos archivos trace.json o ambos carpetas con <escenario>/trace.json")


def _etiqueta_cambio(fila):
    if fila["diferencia"] == 0:
        return "="
    if fila["cambio_pct"] is not None:
        return f"{fila['cambio_pct']:+g} %"
    return f"{fila['diferencia']:+g}"


def grafica_mejora(comparaciones, destino):
    """Un panel por métrica principal; en cada escenario, un punto claro (línea base) unido a uno oscuro
    (nueva corrida), con el cambio en % al lado."""
    plots._estilo()
    nombres = list(comparaciones)
    metricas = plots.METRICAS_COMPARACION
    columnas = 4
    filas = -(-len(metricas) // columnas)
    alto_panel = 1.7 + 0.55 * len(nombres)
    fig, ejes = plt.subplots(filas, columnas, figsize=(14, alto_panel * filas + 0.6), squeeze=False)
    for ax, (clave, titulo) in zip(ejes.flat, metricas):
        sentido = next((c["metricas"][clave]["sentido"] for c in comparaciones.values() if clave in c["metricas"]),
                       "neutro")
        valores = []
        for i, nombre in enumerate(nombres):
            fila = comparaciones[nombre]["metricas"].get(clave)
            y = len(nombres) - 1 - i
            if not fila or fila["base"] is None or fila["nueva"] is None:
                ax.text(0, y, "  sin datos", va="center", color=plots.TINTA_TENUE, fontsize=8)
                continue
            b, n = fila["base"], fila["nueva"]
            valores += [b, n]
            ax.plot([b, n], [y, y], color=plots.EJE, linewidth=2, solid_capstyle="round", zorder=1)
            ax.plot([b], [y], "o", markersize=8, color=COLOR_BASE, markeredgecolor=plots.SUPERFICIE,
                    markeredgewidth=2, zorder=3)
            ax.plot([n], [y], "o", markersize=8, color=COLOR_NUEVA, markeredgecolor=plots.SUPERFICIE,
                    markeredgewidth=2, zorder=4)
            ax.annotate(_etiqueta_cambio(fila), (max(b, n), y), xytext=(9, 0), textcoords="offset points",
                        va="center", color=plots.TINTA_2, fontsize=8)
        ax.set_title(f"{titulo}\n({NOTA_SENTIDO[sentido]})", fontsize=10)
        ax.set_yticks(range(len(nombres)))
        ax.set_yticklabels(list(reversed(nombres)), fontsize=9)
        ax.set_ylim(-0.7, len(nombres) - 0.3)
        # los puntos marcan posición (no longitud): el eje se ajusta al rango para que se vean los cambios
        if valores:
            minimo, maximo = min(valores), max(valores)
            margen = (maximo - minimo) * 0.35 or max(abs(maximo) * 0.1, 1)
            ax.set_xlim(minimo - margen, maximo + margen * 1.6)
        ax.grid(axis="y", visible=False)
    for ax in list(ejes.flat)[len(metricas):]:
        ax.set_visible(False)
    asas = [Line2D([0], [0], marker="o", linestyle="none", markersize=8, color=COLOR_BASE, label="Línea base"),
            Line2D([0], [0], marker="o", linestyle="none", markersize=8, color=COLOR_NUEVA, label="Nueva corrida")]
    fig.legend(handles=asas, loc="lower center", ncol=2)
    fig.suptitle("Nueva corrida contra la línea base", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    return plots._guardar(fig, destino)


def _texto(valor):
    return "—" if valor is None else f"{valor:g}"


def tablas_de_cambios(comparaciones, destino_csv, destino_md):
    """CSV con todas las métricas de todos los escenarios; Markdown con las métricas principales."""
    destino_csv, destino_md = Path(destino_csv), Path(destino_md)
    destino_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(destino_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(COLUMNAS_CSV)
        for nombre, comp in comparaciones.items():
            for metrica, fila in comp["metricas"].items():
                w.writerow([nombre, metrica] + ["" if fila[c] is None else fila[c] for c in COLUMNAS_CSV[2:]])

    lineas = ["| Escenario | Métrica | Línea base | Nueva | Cambio | Resultado |", "|---|---|---|---|---|---|"]
    for nombre, comp in comparaciones.items():
        for clave, titulo in plots.METRICAS_COMPARACION:
            fila = comp["metricas"].get(clave)
            if fila:
                lineas.append(f"| {nombre} | {titulo.replace(chr(10), ' ')} | {_texto(fila['base'])} | "
                              f"{_texto(fila['nueva'])} | {_etiqueta_cambio(fila) if fila['diferencia'] is not None else '—'} | "
                              f"{fila['resultado']} |")
    destino_md.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return destino_csv, destino_md


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compara una corrida nueva contra la línea base del mismo escenario.")
    parser.add_argument("base", help="trace.json de la línea base, o carpeta con <escenario>/trace.json")
    parser.add_argument("nueva", help="trace.json de la corrida nueva, o carpeta con <escenario>/trace.json")
    parser.add_argument("--salida", default=str(SALIDA_POR_DEFECTO),
                        help="carpeta de salida (default: runs/comparacion_linea_base)")
    parser.add_argument("--parametros", help="JSON con los parámetros de combustible y precios que cambian")
    args = parser.parse_args(argv)
    parametros = cargar_parametros(args.parametros) if args.parametros else None

    try:
        pares, sin_pareja = emparejar(args.base, args.nueva)
    except ValueError as exc:
        print(f"error: {exc}")
        return 1
    for nombre in sin_pareja:
        print(f"aviso: {nombre} no tiene corrida nueva; se omite")
    if not pares:
        print("error: no hay escenarios para comparar")
        return 1

    comparaciones = {}
    for nombre, ruta_base, ruta_nueva in pares:
        try:
            comparaciones[nombre] = comparar_corridas(cargar_trace(ruta_base), cargar_trace(ruta_nueva), parametros)
        except ValueError as exc:
            print(f"error en {nombre}: {exc}")
            return 1
        comp = comparaciones[nombre]
        ocio = comp["metricas"]["tiempo_ocioso_cosechadora"]
        r = comp["resumen"]
        print(f"{nombre}: tiempo ocioso {ocio['base']} -> {ocio['nueva']} ({_etiqueta_cambio(ocio)}, {ocio['resultado']}); "
              f"{r['mejora']} mejoran, {r['empeora']} empeoran, {r['igual']} iguales")
        if comp["diferencias_config"]:
            print(f"  config distinta en: {comp['diferencias_config']}")

    salida = Path(args.salida)
    for ruta in (grafica_mejora(comparaciones, salida / "mejora_vs_linea_base.png"),
                 *tablas_de_cambios(comparaciones, salida / "cambios.csv", salida / "cambios.md")):
        print(ruta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
