"""Visor 2D que reproduce un trace.json.  [Bloque D]

Especificación: §7.1. NO debe importar nada de harvest_sim (solo lee el JSON), para
que el mismo log sirva después para Unity. Si falta un dato, agrégalo al log.

Uso: python viz/viewer.py runs/escenario_a/trace.json

Debe mostrar: grid; celdas cosechadas vs. por cosechar; bodega y casillas de inicio;
agentes con orientación; barra de carga; estado como texto; número de tick;
estela. Controles: pausa/reanudar, paso a paso, velocidad ajustable.
Herramienta sugerida: pygame.
"""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Reproduce un trace.json en 2D.")
    parser.add_argument("trace", help="ruta a trace.json")
    parser.parse_args()
    raise NotImplementedError("Bloque D: viewer")


if __name__ == "__main__":
    raise SystemExit(main())
