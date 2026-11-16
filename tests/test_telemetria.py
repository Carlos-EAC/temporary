"""Telemetría: log v2.0, checksum, reconstrucción y escritura.  [Dueño: Joel]

Los valores esperados están calculados a mano a partir de un guion de 20 ticks (un mapa de 4x3,
una cosechadora y un carro): no salen del código que se prueba.
"""

import copy
import importlib.util
from pathlib import Path

import pytest

from harvest_sim.telemetria import (
    SCHEMA_VERSION,
    TraceBuilder,
    calcular_checksum,
    calcular_metricas,
    cargar_trace,
    con_checksum,
    escribir_trace,
    reconstruir,
    series_temporales,
    verificar_checksums,
)

RAIZ = Path(__file__).resolve().parents[1]
FIXTURE = RAIZ / "tests" / "fixtures" / "trace_ejemplo.json"

H, C = "cosechadora_1", "carro_1"
CAPACIDAD = {H: 4, C: 8}
TIPO = {H: "cosechadora", C: "carro"}
CONFIG = {"nombre": "ejemplo_mini", "seed": 0, "ancho": 4, "alto": 3, "capacidad_cosechadora": 4}
MUNDO = {"ancho": 4, "alto": 3, "bodega": [0, 0], "bases": {C: [1, 0], H: [2, 0]}, "grano_por_celda": 1}
AGENTES = [
    {"id": H, "tipo": "cosechadora", "capacidad": 4, "base": [2, 0]},
    {"id": C, "tipo": "carro", "capacidad": 8, "base": [1, 0]},
]
TOTAL = 20


def pose(x, y, o):
    return {"x": x, "y": y, "orientacion": o}


def cel(celda, agente=H):
    return {"tipo": "CELDA_COSECHADA", "celda": celda, "agente": agente}


def enviado(i, tipo_mensaje, de, a, payload, entrega_en):
    return {"tipo": "MENSAJE_ENVIADO", "id": i, "tipo_mensaje": tipo_mensaje, "de": de, "a": a,
            "payload": payload, "entrega_en": entrega_en}


def entregado(i, a):
    return {"tipo": "MENSAJE_ENTREGADO", "id": i, "a": a}


def deposito(agente, cantidad, total):
    return {"tipo": "DEPOSITO", "agente": agente, "cantidad": cantidad, "entregado_total": total}


def bloqueo(agente):
    return {"tipo": "BLOQUEO", "agente": agente}


# Qué campos cambian en cada tick (los demás se mantienen). Los ticks 12, 18 y 20 no cambian nada.
GUION = {
    0: {H: dict(pose=pose(2, 0, "S"), estado="EN_BASE", carga=0),
        C: dict(pose=pose(1, 0, "N"), estado="EN_BASE", carga=0)},
    1: {H: dict(estado="YENDO_A_CAMPO")},
    2: {H: dict(pose=pose(2, 1, "S"))},
    3: {H: dict(pose=pose(1, 1, "O"))},
    4: {H: dict(pose=pose(0, 1, "O"), estado="COSECHANDO", carga=1)},
    5: {H: dict(pose=pose(1, 1, "E"), carga=2)},
    6: {H: dict(pose=pose(2, 1, "E"), carga=3)},
    7: {H: dict(pose=pose(3, 1, "E"), carga=4, estado="LLENA_ESPERANDO")},
    8: {C: dict(estado="YENDO_A_COSECHADORA")},
    9: {C: dict(pose=pose(2, 0, "E"))},
    10: {C: dict(pose=pose(3, 0, "E"), estado="ESPERANDO_TRANSFERENCIA")},
    11: {H: dict(estado="TRANSFIRIENDO")},
    13: {H: dict(carga=0, estado="COSECHANDO"), C: dict(carga=4)},
    14: {H: dict(pose=pose(3, 2, "S"), carga=1), C: dict(estado="YENDO_A_BODEGA")},
    15: {C: dict(pose=pose(2, 0, "O"))},
    16: {C: dict(pose=pose(1, 0, "O"))},
    17: {C: dict(pose=pose(0, 0, "O"), estado="DESCARGANDO")},
    19: {C: dict(carga=0, estado="REGRESANDO_A_BASE")},
}
EVENTOS = {
    4: [cel([0, 1])],
    5: [cel([1, 1])],
    6: [cel([2, 1])],
    7: [cel([3, 1]), enviado(1, "LLENA", H, C, {"x": 3, "y": 1, "carga": 4}, 8)],
    8: [entregado(1, C)],
    13: [enviado(2, "TRANSFERENCIA_TERMINADA", H, C, {"cantidad": 4}, 14)],
    14: [entregado(2, C), cel([3, 2])],
    17: [bloqueo(H)],
    19: [deposito(C, 4, 4)],
}


def registro(tick, agente, e):
    return {
        "tick": tick, "agent_id": agente, "tipo": TIPO[agente],
        "pose": copy.deepcopy(e["pose"]), "estado": e["estado"],
        "carga": {"actual": e["carga"], "capacidad": CAPACIDAD[agente]},
    }


def densos():
    """(tick, registros completos, eventos) para los ticks 0..TOTAL, con el estado arrastrado."""
    estado = {H: {}, C: {}}
    salida = []
    for t in range(TOTAL + 1):
        for agente, campos in GUION.get(t, {}).items():
            estado[agente].update(copy.deepcopy(campos))
        salida.append((t, [registro(t, a, estado[a]) for a in (H, C)], copy.deepcopy(EVENTOS.get(t, []))))
    return salida


def construir_trace():
    b = TraceBuilder(CONFIG, MUNDO, AGENTES)
    entradas = densos()
    for t, regs, evs in entradas:
        b.agregar_tick(t, regs, evs)
    return b.construir(), entradas


def por_tick(trace):
    return {t["tick"]: t for t in trace["ticks"]}


def test_checksum_es_estable_e_ignora_el_campo_checksum():
    """Humo del contrato: 16 hex, independiente del orden de claves, ignora `checksum`."""
    registro_ = {"tick": 3, "agent_id": "carro_1", "estado": "EN_BASE"}
    c = calcular_checksum(registro_)
    assert len(c) == 16 and all(ch in "0123456789abcdef" for ch in c)
    assert c == calcular_checksum({"estado": "EN_BASE", "agent_id": "carro_1", "tick": 3})
    assert c == calcular_checksum({**registro_, "checksum": "otro"})
    assert con_checksum(registro_)["checksum"] == c


def test_estructura_trace_v2():
    """El trace construido tiene schema_version 2.0, meta, config, mundo, agentes, ticks (arreglo
    ordenado) y metricas, coherentes con el config."""
    trace, _ = construir_trace()
    assert list(trace) == ["schema_version", "meta", "config", "mundo", "agentes", "ticks", "metricas"]
    assert trace["schema_version"] == "2.0" == SCHEMA_VERSION
    assert trace["meta"] == {"escenario": "ejemplo_mini", "seed": 0, "total_ticks": TOTAL}
    assert trace["config"] == CONFIG and trace["mundo"] == MUNDO and trace["agentes"] == AGENTES
    assert trace["metricas"] == {}
    assert isinstance(trace["ticks"], list)
    numeros = [t["tick"] for t in trace["ticks"]]
    assert numeros == sorted(set(numeros))
    assert all(list(t) == ["tick", "cambios", "checksum"] for t in trace["ticks"])


def test_ticks_sin_cambios_no_aparecen():
    """Un tick sin cambios no aparece; el tick 0 siempre aparece; meta.total_ticks es el último tick."""
    trace, _ = construir_trace()
    presentes = [t["tick"] for t in trace["ticks"]]
    assert presentes == [t for t in range(TOTAL + 1) if t not in (12, 18, 20)]
    assert trace["meta"]["total_ticks"] == 20  # el último tick no tiene cambios y aun así cuenta

    b = TraceBuilder({}, {}, [])
    b.agregar_tick(0, [], [])  # el tick 0 aparece aunque esté vacío
    assert [t["tick"] for t in b.construir()["ticks"]] == [0]


def test_diff_de_agente_solo_campos_que_cambian():
    """Un AGENTE.set contiene solo los campos que cambiaron y cada campo va completo."""
    trace, _ = construir_trace()
    ticks = por_tick(trace)
    # tick 0: los tres campos de cada agente
    sets0 = {e["id"]: e["set"] for e in ticks[0]["cambios"]}
    assert sets0 == {
        H: {"pose": pose(2, 0, "S"), "estado": "EN_BASE", "carga": 0},
        C: {"pose": pose(1, 0, "N"), "estado": "EN_BASE", "carga": 0},
    }
    # tick 1: solo el estado de la cosechadora; el carro, quieto, no genera nada
    assert ticks[1]["cambios"] == [{"tipo": "AGENTE", "id": H, "set": {"estado": "YENDO_A_CAMPO"}}]
    # tick 5: pose entera y carga, sin estado; la carga es un entero
    agente5 = [e for e in ticks[5]["cambios"] if e["tipo"] == "AGENTE"]
    assert agente5 == [{"tipo": "AGENTE", "id": H, "set": {"pose": pose(1, 1, "E"), "carga": 2}}]
    assert isinstance(agente5[0]["set"]["carga"], int)


def test_diff_ignora_campos_extra_y_no_depende_de_referencias():
    """Los campos que no son pose, estado ni carga se ignoran, y el builder no se confunde si el
    agente muta su propio registro entre ticks."""
    b = TraceBuilder(CONFIG, MUNDO, AGENTES)
    r = registro(0, H, {"pose": pose(2, 0, "S"), "estado": "EN_BASE", "carga": 0})
    r["intencion"] = {"accion": "NINGUNA", "celdas": []}
    r["objetivo"] = None
    b.agregar_tick(0, [r], [])
    r["pose"]["x"] = 3  # el agente muta su registro en el lugar
    b.agregar_tick(1, [r], [])
    ticks = b.construir()["ticks"]
    assert set(ticks[0]["cambios"][0]["set"]) == {"pose", "estado", "carga"}
    assert ticks[1]["cambios"] == [{"tipo": "AGENTE", "id": H, "set": {"pose": pose(3, 0, "S")}}]


def test_orden_de_eventos_dentro_del_tick():
    """Orden fijo: MENSAJE_ENTREGADO, AGENTE (cosechadora y luego carro), CELDA_COSECHADA,
    DEPOSITO y BLOQUEO (en el orden recibido), MENSAJE_ENVIADO."""
    trace, _ = construir_trace()
    tick14 = por_tick(trace)[14]["cambios"]
    assert [e["tipo"] for e in tick14] == ["MENSAJE_ENTREGADO", "AGENTE", "AGENTE", "CELDA_COSECHADA"]
    assert [e["id"] for e in tick14 if e["tipo"] == "AGENTE"] == [H, C]

    b = TraceBuilder(CONFIG, MUNDO, AGENTES)
    base = {H: dict(pose=pose(2, 0, "S"), estado="EN_BASE", carga=0),
            C: dict(pose=pose(1, 0, "N"), estado="EN_BASE", carga=0)}
    b.agregar_tick(0, [registro(0, a, base[a]) for a in (H, C)], [])
    nuevo = {H: dict(base[H], carga=1), C: dict(base[C], estado="YENDO_A_COSECHADORA")}
    revueltos = [
        enviado(7, "LLENA", H, C, {}, 2),
        bloqueo(C),
        deposito(C, 4, 4),
        cel([0, 1]),
        entregado(6, H),
    ]
    b.agregar_tick(1, [registro(1, a, nuevo[a]) for a in (H, C)], revueltos)
    cambios = b.construir()["ticks"][1]["cambios"]
    assert [e["tipo"] for e in cambios] == [
        "MENSAJE_ENTREGADO", "AGENTE", "AGENTE", "BLOQUEO", "DEPOSITO", "CELDA_COSECHADA", "MENSAJE_ENVIADO",
    ]


def test_entradas_invalidas():
    """Ticks no crecientes, eventos AGENTE o desconocidos en `eventos` y construir sin ticks fallan."""
    b = TraceBuilder(CONFIG, MUNDO, AGENTES)
    with pytest.raises(ValueError):
        b.construir()
    b.agregar_tick(0, [], [])
    with pytest.raises(ValueError):
        b.agregar_tick(0, [], [])
    with pytest.raises(ValueError):
        b.agregar_tick(1, [], [{"tipo": "AGENTE", "id": H, "set": {}}])
    with pytest.raises(ValueError):
        b.agregar_tick(1, [], [{"tipo": "INVENTADO"}])


def test_reconstruir_estado_por_tick():
    """reconstruir(trace) devuelve el estado de cada tick, incluidos los ticks sin cambios."""
    trace, entradas = construir_trace()
    estados = list(reconstruir(trace))
    assert [e["tick"] for e in estados] == list(range(TOTAL + 1))
    # coincide con el estado completo que tenía cada agente en cada tick
    for e, (t, regs, _) in zip(estados, entradas):
        esperado = {r["agent_id"]: {"pose": r["pose"], "estado": r["estado"], "carga": r["carga"]["actual"]}
                    for r in regs}
        assert e["agentes"] == esperado, t
    # valores calculados a mano
    assert estados[12]["eventos"] == []
    assert estados[12]["agentes"][H]["estado"] == "TRANSFIRIENDO"  # se arrastra desde el tick 11
    assert estados[7]["celdas_cosechadas"] == [[0, 1], [1, 1], [2, 1], [3, 1]]
    assert estados[7]["mensajes_en_transito"] == [1] and estados[8]["mensajes_en_transito"] == []
    assert estados[13]["mensajes_en_transito"] == [2] and estados[14]["mensajes_en_transito"] == []
    assert estados[18]["entregado_total"] == 0 and estados[19]["entregado_total"] == 4
    assert [e["tipo"] for e in estados[17]["eventos"]] == ["AGENTE", "BLOQUEO"]
    assert estados[20]["agentes"][C]["estado"] == "REGRESANDO_A_BASE"
    # cada elemento es una copia independiente
    estados[0]["agentes"][H]["carga"] = 99
    assert list(reconstruir(trace))[0]["agentes"][H]["carga"] == 0
    # ticks desordenados se rechazan
    malo = copy.deepcopy(trace)
    malo["ticks"][1], malo["ticks"][2] = malo["ticks"][2], malo["ticks"][1]
    with pytest.raises(ValueError):
        list(reconstruir(malo))


def test_checksum_de_cada_tick_del_log():
    """Cada tick de un trace verifica su checksum al recalcularlo; una alteración se detecta."""
    trace, _ = construir_trace()
    assert verificar_checksums(trace)
    for t in trace["ticks"]:
        assert t["checksum"] == calcular_checksum({"tick": t["tick"], "cambios": t["cambios"]})
    alterado = copy.deepcopy(trace)
    alterado["ticks"][5]["cambios"][0]["set"]["carga"] = 3
    assert not verificar_checksums(alterado)
    sin_checksum = copy.deepcopy(trace)
    del sin_checksum["ticks"][0]["checksum"]
    assert not verificar_checksums(sin_checksum)


def test_escritura_reproducible(tmp_path):
    """Escribir dos veces el mismo trace produce archivos idénticos; schema_version queda primero."""
    trace1, _ = construir_trace()
    trace2, _ = construir_trace()  # otra corrida con el mismo guion
    a = tmp_path / "a" / "trace.json"  # la carpeta no existe: se crea
    b = tmp_path / "b.json"
    escribir_trace(trace1, a)
    escribir_trace(trace2, b)
    bytes_a = a.read_bytes()
    assert bytes_a == b.read_bytes()
    assert bytes_a.startswith(b'{\n  "schema_version": "2.0",')
    assert bytes_a.endswith(b"}\n") and b"\r" not in bytes_a
    leido = cargar_trace(a)
    assert leido == trace1 and verificar_checksums(leido)


def cargar_generador():
    spec = importlib.util.spec_from_file_location("generar_trace_ejemplo", RAIZ / "tools" / "generar_trace_ejemplo.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_fixture_es_valido_y_verificable():
    """El fixture existe, es esquema 2.0, pasa los checksums y se puede reconstruir completo."""
    trace = cargar_trace(FIXTURE)
    assert trace["schema_version"] == "2.0" and verificar_checksums(trace)
    numeros = [t["tick"] for t in trace["ticks"]]
    assert numeros[0] == 0 and numeros == sorted(set(numeros))
    assert [e["tick"] for e in reconstruir(trace)] == list(range(trace["meta"]["total_ticks"] + 1))


def test_fixture_se_regenera_identico(tmp_path):
    """Correr el generador de nuevo produce exactamente el mismo archivo (es determinista)."""
    destino = tmp_path / "otra_vez.json"
    escribir_trace(cargar_generador().generar(), destino)
    assert destino.read_bytes() == FIXTURE.read_bytes()


def test_fixture_cumple_las_reglas_y_cubre_los_casos():
    """Desde el log: inicio y fin en las bases, R2 (un paso por tick), R3 (nunca la misma celda), R7
    (conservación de grano) y los casos que necesitan las métricas: espera, carga parcial final,
    bloqueo, depósitos y mensajes bien emparejados."""
    trace = cargar_trace(FIXTURE)
    estados = list(reconstruir(trace))
    bases = {a["id"]: tuple(a["base"]) for a in trace["agentes"]}
    posicion = lambda e, a: (e["agentes"][a]["pose"]["x"], e["agentes"][a]["pose"]["y"])  # noqa: E731

    # inicio y fin
    assert {a: posicion(estados[0], a) for a in (H, C)} == bases
    assert {a: posicion(estados[-1], a) for a in (H, C)} == bases
    assert estados[-1]["agentes"][H]["estado"] == "FIN" and estados[-1]["agentes"][C]["estado"] == "EN_BASE"

    # R2, R3 y R7 en cada tick
    for anterior, e in zip(estados, estados[1:]):
        for a in (H, C):
            (x0, y0), (x1, y1) = posicion(anterior, a), posicion(e, a)
            assert abs(x0 - x1) + abs(y0 - y1) <= 1, (e["tick"], a)
    for e in estados:
        assert posicion(e, H) != posicion(e, C), e["tick"]
        en_agentes = sum(e["agentes"][a]["carga"] for a in (H, C))
        assert len(e["celdas_cosechadas"]) == en_agentes + e["entregado_total"], e["tick"]

    campo = trace["mundo"]["ancho"] * (trace["mundo"]["alto"] - 1)
    assert len(estados[-1]["celdas_cosechadas"]) == campo == estados[-1]["entregado_total"]
    assert len({tuple(c) for c in estados[-1]["celdas_cosechadas"]}) == campo  # ninguna celda dos veces

    eventos = [(e["tick"], ev) for e in estados for ev in e["eventos"]]
    # espera por el carro, bloqueo y depósitos
    assert any(e["agentes"][H]["estado"] == "LLENA_ESPERANDO" for e in estados)
    assert sum(1 for _, ev in eventos if ev["tipo"] == "BLOQUEO") >= 1
    assert sum(ev["cantidad"] for _, ev in eventos if ev["tipo"] == "DEPOSITO") == campo
    # carga parcial final: la última carga que avisa la cosechadora es menor que su capacidad
    llenas = [ev["payload"]["carga"] for _, ev in eventos
              if ev["tipo"] == "MENSAJE_ENVIADO" and ev["tipo_mensaje"] == "LLENA"]
    assert llenas[-1] < trace["agentes"][0]["capacidad"] and len(llenas) >= 2
    # cada mensaje enviado se entrega en el tick siguiente, con id único y creciente
    enviados = [(t, ev) for t, ev in eventos if ev["tipo"] == "MENSAJE_ENVIADO"]
    entregas = {ev["id"]: t for t, ev in eventos if ev["tipo"] == "MENSAJE_ENTREGADO"}
    assert [ev["id"] for _, ev in enviados] == list(range(1, len(enviados) + 1))
    for t, ev in enviados:
        assert ev["entrega_en"] == t + 1 and entregas[ev["id"]] == t + 1


ORDEN_METRICAS = [
    "tiempo_ocioso_cosechadora", "tiempo_transfiriendo", "tick_fin_cosecha", "tiempo_completacion",
    "distancia_cosechadora", "distancia_carro", "distancia_total", "colisiones", "ticks_bloqueados",
    "num_ciclos", "espera_por_ciclo", "utilizacion_carro", "grano_total_entregado",
    "porcentaje_ocioso", "ticks_por_estado", "mensajes_enviados", "distancia_cosechadora_carro_promedio",
    "distancia_cosechadora_carro_minima", "distancia_cosechadora_carro_maxima", "grano_cosechado_total",
    "grano_esperado_total", "porcentaje_entregado",
    "combustible_usado", "combustible_usado_total", "combustible_comprado", "combustible_comprado_total",
    "recargas", "combustible_minimo_en_tanque", "combustible_suficiente", "costo_combustible",
    "valor_grano_entregado", "balance",
]


def test_metricas_desde_el_log():
    """Las métricas del fixture coinciden con las calculadas a mano sobre su línea de tiempo:
    cosechadora LLENA_ESPERANDO en 6-10, 19-26 y 32-41; TRANSFIRIENDO en 11-13, 27-29 y 42-43; última
    transferencia en el tick 44; 49 ticks; la cosechadora recorre 3 + 7 + 4 celdas y el carro 8 + 6 + 4;
    el carro está en EN_BASE 10 de 50 ticks."""
    trace = cargar_trace(FIXTURE)
    original = copy.deepcopy(trace)
    metricas = calcular_metricas(trace)
    assert list(metricas) == ORDEN_METRICAS
    assert {k: metricas[k] for k in ORDEN_METRICAS[:13]} == {
        "tiempo_ocioso_cosechadora": 23,
        "tiempo_transfiriendo": 8,
        "tick_fin_cosecha": 44,
        "tiempo_completacion": 49,
        "distancia_cosechadora": 14,
        "distancia_carro": 18,
        "distancia_total": 32,
        "colisiones": 0,
        "ticks_bloqueados": {H: 2, C: 0},
        "num_ciclos": 3,
        "espera_por_ciclo": [5, 8, 10],
        "utilizacion_carro": 0.8,
        "grano_total_entregado": 8,
    }
    # una métrica por variable en juego, calculadas a mano sobre la misma línea de tiempo
    assert metricas["porcentaje_ocioso"] == 46.0  # 23 de 50 ticks
    assert metricas["ticks_por_estado"] == {
        H: {"EN_BASE": 1, "YENDO_A_CAMPO": 3, "COSECHANDO": 9, "LLENA_ESPERANDO": 23, "TRANSFIRIENDO": 8,
            "REGRESANDO_A_BASE": 4, "FIN": 2},
        C: {"EN_BASE": 10, "YENDO_A_COSECHADORA": 7, "ESPERANDO_TRANSFERENCIA": 14, "YENDO_A_BODEGA": 8,
            "DESCARGANDO": 8, "REGRESANDO_A_BASE": 3},
    }
    assert metricas["mensajes_enviados"] == {"LLENA": 3, "TRANSFERENCIA_TERMINADA": 3}
    assert (metricas["grano_cosechado_total"], metricas["grano_esperado_total"],
            metricas["porcentaje_entregado"]) == (8, 8, 100.0)
    # distancia cosechadora-carro: las bases son vecinas (1 celda) y se cumple lo que dicen las series
    distancias = series_temporales(trace)["distancia_cosechadora_carro"]
    assert metricas["distancia_cosechadora_carro_minima"] == min(distancias) == 1
    assert metricas["distancia_cosechadora_carro_maxima"] == max(distancias)
    assert metricas["distancia_cosechadora_carro_promedio"] == round(sum(distancias) / 50, 4)
    assert trace == original  # no modifica el trace


def test_metricas_del_guion_de_20_ticks():
    """Guion de 20 ticks (calculado a mano): LLENA_ESPERANDO 7-10, TRANSFIRIENDO 11-12, una sola carga,
    un bloqueo de la cosechadora, un depósito de 4; la cosechadora avanza 7 celdas y el carro 5; el carro
    sale de EN_BASE en el tick 8, así que 13 de 21 ticks."""
    trace, _ = construir_trace()
    metricas = calcular_metricas(trace)
    assert {k: metricas[k] for k in ORDEN_METRICAS[:13]} == {
        "tiempo_ocioso_cosechadora": 4,
        "tiempo_transfiriendo": 2,
        "tick_fin_cosecha": 13,
        "tiempo_completacion": 20,
        "distancia_cosechadora": 7,
        "distancia_carro": 5,
        "distancia_total": 12,
        "colisiones": 0,
        "ticks_bloqueados": {H: 1, C: 0},
        "num_ciclos": 1,
        "espera_por_ciclo": [4],
        "utilizacion_carro": 0.619,
        "grano_total_entregado": 4,
    }
    assert metricas["porcentaje_ocioso"] == 19.05  # 4 de 21 ticks
    assert metricas["ticks_por_estado"] == {
        H: {"EN_BASE": 1, "YENDO_A_CAMPO": 3, "COSECHANDO": 11, "LLENA_ESPERANDO": 4, "TRANSFIRIENDO": 2},
        C: {"EN_BASE": 8, "YENDO_A_COSECHADORA": 2, "ESPERANDO_TRANSFERENCIA": 4, "YENDO_A_BODEGA": 3,
            "DESCARGANDO": 2, "REGRESANDO_A_BASE": 2},
    }
    assert metricas["mensajes_enviados"] == {"LLENA": 1, "TRANSFERENCIA_TERMINADA": 1}
    # distancias Manhattan por tick, 51 en total en 21 ticks: promedio 2.4286, mínima 1 y máxima 5
    assert metricas["distancia_cosechadora_carro_promedio"] == 2.4286
    assert (metricas["distancia_cosechadora_carro_minima"], metricas["distancia_cosechadora_carro_maxima"]) == (1, 5)
    # campo de 4 x 2 = 8 de grano; se cosecharon 5 y llegaron 4 a la bodega: 50 %
    assert (metricas["grano_cosechado_total"], metricas["grano_esperado_total"],
            metricas["porcentaje_entregado"]) == (5, 8, 50.0)


def test_series_temporales_del_guion():
    """Series por tick del guion de 20 ticks, calculadas a mano: el ocioso acumulado sube 1 por tick entre
    los ticks 7 y 10 y queda plano; la distancia es Manhattan; el grano entra a la bodega en el tick 19."""
    trace, _ = construir_trace()
    s = series_temporales(trace)
    assert s["tick"] == list(range(21))
    assert s["ocioso_acumulado"] == [0] * 7 + [1, 2, 3, 4] + [4] * 10
    assert s["distancia_cosechadora_carro"] == [1, 1, 2, 1, 2, 1, 2, 3, 3, 2, 1, 1, 1, 1, 2, 3, 4, 5, 5, 5, 5]
    assert s["carga_cosechadora"] == [0] * 4 + [1, 2, 3] + [4] * 6 + [0] + [1] * 7
    assert s["carga_carro"] == [0] * 13 + [4] * 6 + [0] * 2
    assert s["cosechado_acumulado"] == [0] * 4 + [1, 2, 3, 4] + [4] * 6 + [5] * 7
    assert s["entregado_en_bodega"] == [0] * 19 + [4, 4]
    assert s["bloqueos_acumulados"] == [0] * 17 + [1] * 4
    # coherencia con las métricas
    m = calcular_metricas(trace)
    assert s["ocioso_acumulado"][-1] == m["tiempo_ocioso_cosechadora"]
    assert s["entregado_en_bodega"][-1] == m["grano_total_entregado"]


def test_series_del_fixture_son_coherentes_con_las_metricas():
    trace = cargar_trace(FIXTURE)
    s, m = series_temporales(trace), calcular_metricas(trace)
    assert all(len(v) == 50 for v in s.values())
    assert s["ocioso_acumulado"][-1] == 23 == m["tiempo_ocioso_cosechadora"]
    assert s["entregado_en_bodega"][-1] == s["cosechado_acumulado"][-1] == 8
    assert s["bloqueos_acumulados"][-1] == 2
    assert all(b >= a for a, b in zip(s["ocioso_acumulado"], s["ocioso_acumulado"][1:]))  # nunca baja


def test_metricas_distancia_ignora_cambios_de_orientacion():
    """Girar sin cambiar de celda no es distancia: (1,0) E -> (1,0) S -> (2,0) S son 1 movimiento."""
    b = TraceBuilder(CONFIG, MUNDO, AGENTES)
    for t, (x, y, o) in enumerate([(1, 0, "E"), (1, 0, "S"), (2, 0, "S")]):
        regs = [registro(t, H, {"pose": pose(x, y, o), "estado": "EN_BASE", "carga": 0}),
                registro(t, C, {"pose": pose(0, 0, "N"), "estado": "EN_BASE", "carga": 0})]
        b.agregar_tick(t, regs, [])
    metricas = calcular_metricas(b.construir())
    assert metricas["distancia_cosechadora"] == 1 and metricas["distancia_carro"] == 0


def test_metricas_detectan_colisiones_y_cuentan_ticks():
    """Misma celda en el tick 1 e intercambio de posiciones en el tick 3: son 2 ticks de colisión.
    Sin mensajes, tick_fin_cosecha es None y no hay ciclos."""
    posiciones = [  # (cosechadora, carro) en cada tick
        ((1, 0), (3, 0)),
        ((2, 0), (2, 0)),  # misma celda
        ((2, 0), (3, 0)),
        ((3, 0), (2, 0)),  # se intercambian: la cosechadora estaba en (2,0) y el carro en (3,0)
    ]
    b = TraceBuilder(CONFIG, MUNDO, AGENTES)
    for t, (ph, pc) in enumerate(posiciones):
        regs = [registro(t, H, {"pose": pose(*ph, "E"), "estado": "EN_BASE", "carga": 0}),
                registro(t, C, {"pose": pose(*pc, "E"), "estado": "EN_BASE", "carga": 0})]
        b.agregar_tick(t, regs, [])
    metricas = calcular_metricas(b.construir())
    assert metricas["colisiones"] == 2
    assert metricas["tick_fin_cosecha"] is None and metricas["num_ciclos"] == 0
    assert metricas["espera_por_ciclo"] == [] and metricas["grano_total_entregado"] == 0
    assert metricas["utilizacion_carro"] == 0.0  # el carro nunca sale de EN_BASE
