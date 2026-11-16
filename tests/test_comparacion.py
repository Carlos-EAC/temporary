"""Comparación contra la línea base (tarea 8 de Datos).  [Dueño: Joel]"""

import copy
import csv
import importlib.util
from pathlib import Path

import pytest

from harvest_sim.telemetria import (
    cargar_trace,
    comparar_corridas,
    comparar_metricas,
    escribir_trace,
    sentido_de_metrica,
)

RAIZ = Path(__file__).resolve().parents[1]
FIXTURE = RAIZ / "tests" / "fixtures" / "trace_ejemplo.json"
PNG = b"\x89PNG\r\n\x1a\n"


def cargar_modulo(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def gen():
    return cargar_modulo("generar_trace_ejemplo", RAIZ / "tools" / "generar_trace_ejemplo.py")


@pytest.fixture(scope="module")
def comparar():
    pytest.importorskip("matplotlib")
    return cargar_modulo("comparar", RAIZ / "viz" / "comparar.py")


# --- Lógica (telemetria.py) ----------------------------------------------------------------------
def test_sentido_de_las_metricas():
    assert sentido_de_metrica("tiempo_ocioso_cosechadora") == "menor"
    assert sentido_de_metrica("tiempo_completacion") == "menor"
    assert sentido_de_metrica("utilizacion_carro") == "mayor"
    assert sentido_de_metrica("porcentaje_entregado") == "mayor"
    assert sentido_de_metrica("num_ciclos") == "neutro"
    assert sentido_de_metrica("ticks_por_estado.cosechadora_1.LLENA_ESPERANDO") == "menor"
    assert sentido_de_metrica("ticks_por_estado.carro_1.EN_BASE") == "menor"
    assert sentido_de_metrica("ticks_por_estado.cosechadora_1.COSECHANDO") == "neutro"
    assert sentido_de_metrica("ticks_bloqueados.carro_1") == "menor"
    assert sentido_de_metrica("mensajes_enviados.LLENA") == "neutro"
    assert sentido_de_metrica("metrica_que_no_existe") == "neutro"


def test_comparar_metricas_con_valores_calculados_a_mano():
    base = {"tiempo_ocioso_cosechadora": 20, "utilizacion_carro": 0.5, "num_ciclos": 3, "tick_fin_cosecha": None,
            "espera_por_ciclo": [10, 10], "ticks_por_estado": {"c": {"LLENA_ESPERANDO": 10, "COSECHANDO": 5}}}
    nueva = {"tiempo_ocioso_cosechadora": 15, "utilizacion_carro": 0.6, "num_ciclos": 4, "tick_fin_cosecha": 30,
             "espera_por_ciclo": [8, 7], "ticks_por_estado": {"c": {"LLENA_ESPERANDO": 8, "COSECHANDO": 5,
                                                                    "TRANSFIRIENDO": 2}}}
    filas = comparar_metricas(base, nueva)
    assert filas["tiempo_ocioso_cosechadora"] == {"base": 20, "nueva": 15, "diferencia": -5, "cambio_pct": -25.0,
                                                  "sentido": "menor", "resultado": "mejora"}
    assert filas["utilizacion_carro"] == {"base": 0.5, "nueva": 0.6, "diferencia": 0.1, "cambio_pct": 20.0,
                                          "sentido": "mayor", "resultado": "mejora"}
    assert filas["num_ciclos"]["resultado"] == "distinto"  # informativa: cambió, pero no es mejora ni empeora
    assert filas["tick_fin_cosecha"]["resultado"] == "sin datos"
    assert filas["ticks_por_estado.c.LLENA_ESPERANDO"]["resultado"] == "mejora"  # 10 -> 8
    assert filas["ticks_por_estado.c.COSECHANDO"]["resultado"] == "igual"
    # un estado que no aparece en la base cuenta como 0; el cambio en % no existe (la base es 0)
    assert filas["ticks_por_estado.c.TRANSFIRIENDO"] == {"base": 0, "nueva": 2, "diferencia": 2, "cambio_pct": None,
                                                         "sentido": "neutro", "resultado": "distinto"}
    assert "espera_por_ciclo" not in filas  # las listas no se comparan


def test_empeorar_se_detecta_en_ambos_sentidos():
    filas = comparar_metricas({"tiempo_completacion": 40, "porcentaje_entregado": 100.0},
                              {"tiempo_completacion": 44, "porcentaje_entregado": 87.5})
    assert filas["tiempo_completacion"]["resultado"] == "empeora"
    assert filas["porcentaje_entregado"]["resultado"] == "empeora"
    assert filas["porcentaje_entregado"]["cambio_pct"] == -12.5


def test_una_corrida_contra_si_misma_no_cambia():
    trace = cargar_trace(FIXTURE)
    comp = comparar_corridas(trace, copy.deepcopy(trace))
    assert comp["escenario"] == "ejemplo_fixture" and comp["diferencias_config"] == []
    assert {f["resultado"] for f in comp["metricas"].values()} == {"igual"}
    assert comp["resumen"]["mejora"] == comp["resumen"]["empeora"] == 0


def test_solo_se_comparan_corridas_del_mismo_escenario(gen):
    base = cargar_trace(FIXTURE)
    otro_mapa = gen.generar(dict(gen.CONFIG, ancho=5))
    with pytest.raises(ValueError, match="mundo"):
        comparar_corridas(base, otro_mapa)
    otra_seed = copy.deepcopy(base)
    otra_seed["meta"]["seed"] = 7
    with pytest.raises(ValueError, match="seed"):
        comparar_corridas(base, otra_seed)


def test_otra_config_se_permite_y_se_informa():
    base = cargar_trace(FIXTURE)
    nueva = copy.deepcopy(base)
    nueva["config"]["estrategia"] = "despacho_anticipado"
    assert comparar_corridas(base, nueva)["diferencias_config"] == ["estrategia"]


def test_corrida_sin_el_bloqueo_construido(gen):
    """Mismo escenario, otra corrida: sin el bloqueo construido del primer viaje (con capacidad mayor que 1
    ningún bloqueo ocurre solo), así que los bloqueos de la cosechadora pasan de 2 a 0."""
    base, nueva = gen.generar(), gen.generar(forzar_bloqueo=False)
    comp = comparar_corridas(base, nueva)
    fila = comp["metricas"]["ticks_bloqueados.cosechadora_1"]
    assert (fila["base"], fila["nueva"], fila["resultado"]) == (2, 0, "mejora")
    for f in comp["metricas"].values():  # coherencia de cada fila
        if f["base"] is not None and f["nueva"] is not None:
            assert f["diferencia"] == pytest.approx(f["nueva"] - f["base"])
    assert sum(comp["resumen"].values()) == len(comp["metricas"])


# --- Script (viz/comparar.py) --------------------------------------------------------------------
def preparar_carpetas(gen, raiz):
    gen.generar_escenarios(raiz / "base")
    gen.generar_escenarios(raiz / "nueva", forzar_bloqueo=False)
    return raiz / "base", raiz / "nueva"


def test_cli_compara_carpetas_y_genera_grafica_y_tablas(gen, comparar, tmp_path, capsys):
    base, nueva = preparar_carpetas(gen, tmp_path)
    salida = tmp_path / "salida"
    assert comparar.main([str(base), str(nueva), "--salida", str(salida)]) == 0
    texto = capsys.readouterr().out
    for nombre in ("ejemplo_a", "ejemplo_b", "ejemplo_c"):
        assert f"{nombre}: tiempo ocioso" in texto
    assert (salida / "mejora_vs_linea_base.png").read_bytes().startswith(PNG)

    with open(salida / "cambios.csv", encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    assert list(filas[0]) == comparar.COLUMNAS_CSV
    assert {f["escenario"] for f in filas} == {"ejemplo_a", "ejemplo_b", "ejemplo_c"}
    bloqueos_a = next(f for f in filas if f["escenario"] == "ejemplo_a" and f["metrica"] == "ticks_bloqueados.cosechadora_1")
    assert (bloqueos_a["base"], bloqueos_a["nueva"], bloqueos_a["resultado"]) == ("2", "0", "mejora")

    lineas = (salida / "cambios.md").read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 2 + 3 * len(comparar.plots.METRICAS_COMPARACION)
    assert lineas[0] == "| Escenario | Métrica | Línea base | Nueva | Cambio | Resultado |"


def test_cli_con_dos_archivos(gen, comparar, tmp_path):
    base, nueva = preparar_carpetas(gen, tmp_path)
    assert comparar.main([str(base / "ejemplo_a" / "trace.json"), str(nueva / "ejemplo_a" / "trace.json"),
                          "--salida", str(tmp_path / "salida")]) == 0


def test_cli_avisa_si_falta_una_pareja_o_no_coinciden(gen, comparar, tmp_path, capsys):
    base, nueva = preparar_carpetas(gen, tmp_path)
    (nueva / "ejemplo_c" / "trace.json").unlink()
    assert comparar.main([str(base), str(nueva), "--salida", str(tmp_path / "s1")]) == 0
    assert "ejemplo_c no tiene corrida nueva" in capsys.readouterr().out

    # emparejar escenarios distintos con el mismo nombre de carpeta: se rechaza
    escribir_trace(cargar_trace(base / "ejemplo_b" / "trace.json"), nueva / "ejemplo_a" / "trace.json")
    assert comparar.main([str(base), str(nueva), "--salida", str(tmp_path / "s2")]) == 1
    assert "no son del mismo escenario" in capsys.readouterr().out

    assert comparar.main([str(base), str(nueva / "ejemplo_a" / "trace.json")]) == 1  # carpeta contra archivo
