# harvest_sim — Línea base reactiva de cosecha (2D)

Reto agrícola multiagente · Equipo 3 · TC2008B.
Simulación 2D en Python de **una cosechadora y un carro recolector**. Es la línea base contra la que se compararán las mejoras de coordinación. Python genera un log JSON (`trace.json`); el visor y las gráficas solo leen ese archivo.

> **Estado:** esqueleto. La estructura, los contratos y los tests pendientes están listos; la lógica está por implementar.
> **La referencia de qué construir es [`docs/especificacion_primera_entrega.md`](docs/especificacion_primera_entrega.md).** Léela antes de tocar código.

## Instalación

Requiere Python 3.12.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## Uso

```bash
# Correr un escenario (genera runs/<escenario>/trace.json y gráficas)
python -m harvest_sim.cli config/escenario_a.json

# Visor 2D y gráficas, a partir del log
python viz/viewer.py runs/escenario_a/trace.json
python viz/plots.py runs/escenario_a/trace.json

# Pruebas
pytest
pytest tests/test_mundo.py::test_serpentina_cubre_todo_el_campo   # un solo test
```

Los comandos de CLI, visor y gráficas todavía lanzan `NotImplementedError` (esqueleto).
La simulación es determinista a propósito: no hay aleatoriedad en esta entrega.

## Estructura

```
config/            escenarios (parámetros externos al código)
docs/              especificación y registro de decisiones
src/harvest_sim/   simulación (mundo, mensajes, agentes, telemetría, CLI)
viz/               visor y gráficas (solo leen trace.json)
tests/             una prueba por regla física y por comportamiento
runs/              salidas de las corridas (no se versionan)
```

## Bloques de trabajo

| Bloque | Qué incluye | Archivos |
|---|---|---|
| **A. Mundo y rutas** | grid, bodega, bases, serpentina, BFS, grano, validación de config | `config.py`, `mundo.py`, `config/*.json`, `tests/test_mundo.py`, `tests/test_config.py` |
| **B. Agentes y mensajería** | máquinas de estados, buzón FIFO con ids, conflictos de celda, bucle de ticks | `mensajes.py`, `cosechadora.py`, `carro.py`, `simulacion.py`, `tests/test_mensajes.py`, `tests/test_agentes.py` |
| **C. Telemetría y métricas** | log v1.0, checksum, métricas, gráficas | `telemetria.py`, `viz/plots.py`, `tests/test_telemetria.py` |
| **D. Visor y calidad** | visor, CLI, tests de integración, este README | `viz/viewer.py`, `cli.py`, `tests/test_integracion.py` |

Cada archivo del bloque tiene en su docstring la sección de la especificación que implementa. Los tests pendientes están marcados con `skip`: quita el decorador al implementar cada uno.

## Flujo de trabajo

- Una rama por bloque (`bloque-a-mundo`, `bloque-b-agentes`, …) y pull request hacia `main`.
- El contrato de interfaces (§10 de la especificación) no se cambia sin avisar al equipo y anotarlo en [`docs/decisiones.md`](docs/decisiones.md).
- Todo lo no especificado se decide con la opción más simple y se registra en `docs/decisiones.md`.
