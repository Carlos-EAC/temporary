"""Combustible y gasto calculados desde el log.  [Dueño: Joel]

Modelo: cada agente empieza con el tanque lleno; gasta por cada celda recorrida y, con el motor encendido,
por cada tick quieto; en EN_BASE o FIN el motor está apagado y el tanque se recarga por completo. Se cobra el
tanque inicial completo más cada recarga. Los valores esperados están calculados a mano.
"""

import importlib.util
import json
from pathlib import Path

import pytest
from test_telemetria import C, H, construir_trace  # guion de 20 ticks

from harvest_sim.telemetria import (
    PARAMETROS_POR_DEFECTO,
    calcular_metricas,
    cargar_parametros,
    cargar_trace,
    comparar_corridas,
    metricas_economicas,
    parametros_economicos,
    series_combustible,
)

RAIZ = Path(__file__).resolve().parents[1]
FIXTURE = RAIZ / "tests" / "fixtures" / "trace_ejemplo.json"

# Parámetros de prueba con números fáciles de seguir a mano
PARAMETROS_GUION = {
    "capacidad_tanque": {"cosechadora": 100, "carro": 50},
    "consumo_por_celda": {"cosechadora": 2, "carro": 1},
    "consumo_por_tick_encendido": {"cosechadora": 0.5, "carro": 0.25},
    "precio_por_litro": 1,
    "valor_por_unidad_de_grano": 10,
}


def test_combustible_del_guion_calculado_a_mano():
    """Cosechadora: 7 celdas recorridas (ticks 2-7 y 14) x 2 = 14 L, y 13 ticks quieta con el motor encendido
    (1, 8-13 y 15-20) x 0,5 = 6,5 L: 20,5 L. Carro: 5 celdas (9, 10, 15, 16, 17) x 1 = 5 L, y 8 ticks quieto con
    el motor encendido (8, 11-14 y 18-20) x 0,25 = 2 L: 7 L. Ninguno vuelve a EN_BASE ni a FIN, así que no hay
    recargas: se paga solo el tanque inicial (100 + 50 = 150 $). Llegan 4 de grano a 10 $: 40 $."""
    trace, _ = construir_trace()
    m = metricas_economicas(trace, PARAMETROS_GUION)
    assert m == {
        "combustible_usado": {H: 20.5, C: 7.0},
        "combustible_usado_total": 27.5,
        "combustible_comprado": {H: 100.0, C: 50.0},
        "combustible_comprado_total": 150.0,
        "recargas": {H: 0, C: 0},
        "combustible_minimo_en_tanque": {H: 79.5, C: 43.0},
        "combustible_suficiente": True,
        "costo_combustible": 150.0,
        "valor_grano_entregado": 40.0,
        "balance": -110.0,
    }


def test_series_de_combustible_del_guion():
    trace, _ = construir_trace()
    s = series_combustible(trace, PARAMETROS_GUION)
    assert s["tick"] == list(range(21))
    nivel_h, nivel_c = s[H]["nivel"], s[C]["nivel"]
    assert (nivel_h[0], nivel_h[1], nivel_h[7], nivel_h[20]) == (100.0, 99.5, 87.5, 79.5)
    assert (nivel_c[7], nivel_c[8], nivel_c[17], nivel_c[20]) == (50.0, 49.75, 43.75, 43.0)
    assert s[H]["comprado_acumulado"] == [100.0] * 21  # sin recargas
    assert all(b <= a for a, b in zip(nivel_h, nivel_h[1:]))  # sin recargas, el nivel nunca sube


def test_combustible_del_fixture_con_los_valores_por_defecto():
    """Cosechadora: 14 celdas x 2 = 28 L y 34 ticks quieta con el motor encendido x 0,5 = 17 L (de los 49 ticks,
    14 se mueve y en el 49 ya está en FIN): 45 L. Carro: 18 celdas x 1 = 18 L y 25 ticks quieto con el motor
    encendido x 0,25 = 6,25 L (de los 49, 18 se mueve y en los ticks 1-6 está en EN_BASE): 24,25 L. Ambos terminan en
    su base y recargan, así que lo comprado es el tanque más lo usado. El carro recarga en los ticks 23, 38 y 49 y
    la cosechadora en el 48."""
    m = metricas_economicas(cargar_trace(FIXTURE))
    assert m["combustible_usado"] == {H: 45.0, C: 24.25}
    assert m["combustible_comprado"] == {H: 300.0 + 45.0, C: 100.0 + 24.25}
    assert m["recargas"] == {H: 1, C: 3}
    assert m["combustible_suficiente"] is True
    assert (m["costo_combustible"], m["valor_grano_entregado"], m["balance"]) == (469.25, 80.0, -389.25)
    s = series_combustible(cargar_trace(FIXTURE))
    assert [t for t in s["tick"][1:] if s[C]["comprado_acumulado"][t] > s[C]["comprado_acumulado"][t - 1]] == [23, 38, 49]


def test_tanque_insuficiente_se_reporta():
    trace, _ = construir_trace()
    m = metricas_economicas(trace, dict(PARAMETROS_GUION, capacidad_tanque={"cosechadora": 10, "carro": 50}))
    assert m["combustible_suficiente"] is False
    assert m["combustible_minimo_en_tanque"][H] == pytest.approx(10 - 20.5)


def test_las_metricas_incluyen_el_gasto_y_respetan_los_parametros():
    trace, _ = construir_trace()
    con_defecto = calcular_metricas(trace)
    con_guion = calcular_metricas(trace, PARAMETROS_GUION)
    assert con_guion["balance"] == -110.0
    assert con_defecto["costo_combustible"] != con_guion["costo_combustible"]


def test_parametros_economicos():
    p = parametros_economicos({"precio_por_litro": 2.5, "capacidad_tanque": {"carro": 80}})
    assert p["precio_por_litro"] == 2.5
    assert p["capacidad_tanque"] == {"cosechadora": PARAMETROS_POR_DEFECTO["capacidad_tanque"]["cosechadora"], "carro": 80}
    assert PARAMETROS_POR_DEFECTO["precio_por_litro"] == 1.0  # los valores por defecto no cambian
    with pytest.raises(ValueError, match="desconocido"):
        parametros_economicos({"precio_diesel": 3})
    with pytest.raises(ValueError, match="por tipo"):
        parametros_economicos({"capacidad_tanque": 50})


def test_tipo_de_agente_sin_parametros():
    trace, _ = construir_trace()
    trace["agentes"][1]["tipo"] = "tractor"
    with pytest.raises(ValueError, match="tractor"):
        metricas_economicas(trace)


def test_cargar_parametros_desde_json(tmp_path):
    ruta = tmp_path / "parametros.json"
    ruta.write_text(json.dumps({"valor_por_unidad_de_grano": 100}), encoding="utf-8")
    trace, _ = construir_trace()
    m = metricas_economicas(trace, cargar_parametros(ruta))
    assert m["valor_grano_entregado"] == 400.0  # 4 de grano a 100 $


def test_comparacion_con_el_sentido_del_gasto():
    """Menos combustible y más balance son mejoras: la corrida sin el bloqueo construido recorre menos."""
    spec = importlib.util.spec_from_file_location("generar_trace_ejemplo", RAIZ / "tools" / "generar_trace_ejemplo.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    comp = comparar_corridas(gen.generar(), gen.generar(forzar_bloqueo=False))
    assert comp["metricas"]["costo_combustible"]["sentido"] == "menor"
    assert comp["metricas"]["balance"]["sentido"] == "mayor"
    assert comp["metricas"]["combustible_usado.carro_1"]["sentido"] == "menor"
    assert comp["metricas"]["recargas.carro_1"]["sentido"] == "neutro"
    fila = comp["metricas"]["combustible_usado_total"]
    assert fila["nueva"] < fila["base"] and fila["resultado"] == "mejora"
