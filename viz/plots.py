"""Gráficas a partir de trace.json.  [Bloque C]

Especificación: §7.2. Igual que el visor, solo lee el JSON (no importa la simulación).
Guarda PNG en runs/<escenario>/plots/.

Uso: python viz/plots.py runs/escenario_a/trace.json

Gráficas:
  1. Carga de la cosechadora vs. tiempo (diente de sierra).
  2. Línea de tiempo de estados de ambos agentes (tipo Gantt).
  3. Tiempo ocioso por ciclo (espera_por_ciclo).
  4. Comparación entre escenarios (tiempo ocioso, tick_fin_cosecha,
     tiempo_completacion, distancia_total).
Todas con título, ejes con unidades y leyenda legible.
"""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera las gráficas de una corrida.")
    parser.add_argument("trace", nargs="+", help="uno o más trace.json (la gráfica 4 compara varios)")
    parser.parse_args()
    raise NotImplementedError("Bloque C: plots")


if __name__ == "__main__":
    raise SystemExit(main())
