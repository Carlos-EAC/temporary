"""Gráficas y tabla comparativa (viz/plots.py).  [Dueño: Joel]

Las imágenes se generan sin ventana (backend Agg). Aquí se comprueba que existen, que son PNG válidos y
que la tabla trae los valores correctos; cómo se ven se revisa a ojo.
"""

import copy
import csv
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

from harvest_sim.telemetria import TraceBuilder, cargar_trace, escribir_trace  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
FIXTURE = RAIZ / "tests" / "fixtures" / "trace_ejemplo.json"
PNG = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(scope="module")
def plots():
    spec = importlib.util.spec_from_file_location("plots", RAIZ / "viz" / "plots.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def es_png(ruta):
    datos = Path(ruta).read_bytes()
    return datos.startswith(PNG) and len(datos) > 5000


def con_nombre(trace, nombre):
    otro = copy.deepcopy(trace)
    otro["meta"]["escenario"] = nombre
    return otro


def test_las_tres_graficas_de_un_trace_se_generan(plots, tmp_path):
    rutas = plots.graficas_de_un_trace(FIXTURE, tmp_path)
    assert [r.name for r in rutas] == [
        "1_carga_cosechadora.png", "2_linea_de_tiempo_estados.png", "3_ocio_por_ciclo.png",
    ]
    assert all(es_png(r) for r in rutas)


def test_comparacion_y_tabla_resumen(plots, tmp_path):
    base = cargar_trace(FIXTURE)
    traces = {"escenario_a": con_nombre(base, "escenario_a"), "escenario_b": con_nombre(base, "escenario_b")}
    # en B el carro también se bloquea una vez (un tick que ya tiene cambios): el total de bloqueos pasa a 3
    traces["escenario_b"]["ticks"][10]["cambios"].append({"tipo": "BLOQUEO", "agente": "carro_1"})
    assert es_png(plots.grafica_comparacion(traces, tmp_path / "comparacion.png"))

    ruta_csv, ruta_md = plots.tabla_resumen(traces, tmp_path / "resumen.csv", tmp_path / "resumen.md")
    with open(ruta_csv, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    assert [f["escenario"] for f in filas] == ["escenario_a", "escenario_b"]
    # valores calculados a mano sobre el fixture
    fila = filas[0]
    assert (fila["tiempo_ocioso_cosechadora"], fila["tick_fin_cosecha"], fila["tiempo_completacion"]) == ("23", "44", "49")
    assert (fila["distancia_total"], fila["ticks_bloqueados"], fila["num_ciclos"]) == ("32", "2", "3")
    assert (fila["utilizacion_carro"], fila["grano_total_entregado"], fila["colisiones"]) == ("0.8", "8", "0")
    assert filas[1]["ticks_bloqueados"] == "3"  # suma de los bloqueos de todos los agentes

    lineas = Path(ruta_md).read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 2 + 2  # encabezado, separador y una fila por escenario
    assert lineas[0].startswith("| Escenario | Tiempo ocioso |")
    assert lineas[2].startswith("| escenario_a | 23 | 8 | 44 | 49 |")


def test_todos_los_estados_tienen_categoria_y_color_validado(plots):
    estados = {a["estado"] for t in cargar_trace(FIXTURE)["ticks"] for e in t["cambios"]
               if e["tipo"] == "AGENTE" for a in [e["set"]] if "estado" in a}
    assert estados and estados <= set(plots.CATEGORIA_DE_ESTADO)
    colores = [c[2] for c in plots.CATEGORIAS]
    assert len(set(colores)) == len(colores)  # un color por categoría
    assert set(colores) <= set(plots.SERIES) | {plots.EJE}  # solo la paleta validada y el gris neutro


def test_un_estado_desconocido_se_dibuja_como_otros(plots, tmp_path):
    trace = copy.deepcopy(cargar_trace(FIXTURE))
    trace["ticks"][1]["cambios"][0]["set"]["estado"] = "ESTADO_NUEVO"
    assert es_png(plots.grafica_estados(trace, tmp_path / "estados.png"))


def test_la_comparacion_tiene_limite_de_escenarios(plots, tmp_path):
    base = cargar_trace(FIXTURE)
    demasiados = {f"e{i}": con_nombre(base, f"e{i}") for i in range(len(plots.SERIES) + 1)}
    with pytest.raises(ValueError):
        plots.grafica_comparacion(demasiados, tmp_path / "x.png")


def test_sin_esperas_se_dibuja_un_aviso(plots, tmp_path):
    """Un trace en el que la cosechadora nunca espera genera la gráfica 3 sin fallar."""
    agentes = [{"id": "cosechadora_1", "tipo": "cosechadora", "capacidad": 3, "base": [2, 0]},
               {"id": "carro_1", "tipo": "carro", "capacidad": 6, "base": [1, 0]}]
    b = TraceBuilder({"nombre": "sin_esperas"}, {}, agentes)
    for t in range(3):
        regs = [{"tick": t, "agent_id": a["id"], "tipo": a["tipo"],
                 "pose": {"x": a["base"][0], "y": 0, "orientacion": "S"}, "estado": "EN_BASE",
                 "carga": {"actual": 0, "capacidad": a["capacidad"]}} for a in agentes]
        b.agregar_tick(t, regs, [])
    assert es_png(plots.grafica_espera(b.construir(), tmp_path / "espera.png"))


def test_main_genera_graficas_comparacion_y_tabla(plots, tmp_path, capsys):
    base = cargar_trace(FIXTURE)
    rutas = []
    for nombre in ("escenario_a", "escenario_b"):
        ruta = tmp_path / "entrada" / nombre / "trace.json"
        escribir_trace(con_nombre(base, nombre), ruta)
        rutas.append(str(ruta))
    assert plots.main(rutas + ["--salida", str(tmp_path / "salida")]) == 0
    salida = tmp_path / "salida"
    for nombre in ("escenario_a", "escenario_b"):
        assert es_png(salida / nombre / "2_linea_de_tiempo_estados.png")
    assert es_png(salida / "comparacion" / "4_comparacion_escenarios.png")
    assert (salida / "comparacion" / "resumen.csv").exists() and (salida / "comparacion" / "resumen.md").exists()
    assert str(salida / "comparacion" / "resumen.md") in capsys.readouterr().out
