"""Punto de entrada: python -m harvest_sim.cli config/escenario_a.json  [Bloque D]

Flujo esperado: cargar config -> ejecutar simulación -> escribir
runs/<escenario>/trace.json (con métricas) -> generar gráficas.
"""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Simulación de cosecha (línea base reactiva).")
    parser.add_argument("config", help="ruta al JSON del escenario, p. ej. config/escenario_a.json")
    parser.add_argument("--salida", default="runs", help="carpeta base de salidas (default: runs)")
    parser.add_argument("--sin-plots", action="store_true", help="no generar gráficas")
    nivel = parser.add_mutually_exclusive_group()
    nivel.add_argument("--silencioso", action="store_true", help="log de consola: solo advertencias y errores")
    nivel.add_argument("--detallado", action="store_true", help="log de consola: nivel DEBUG")
    parser.parse_args(argv)
    # TODO (Giovanni): configurar logging (INFO por defecto, formato del §6.3 de la especificación,
    # sin fecha ni hora real) y cablear config.cargar_config, simulacion.ejecutar,
    # telemetria.escribir_trace y viz/plots.py.
    raise NotImplementedError("Bloque D: cli.main")


if __name__ == "__main__":
    raise SystemExit(main())
