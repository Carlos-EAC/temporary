"""Telemetría: log v2.0, checksum, reconstrucción y escritura.  [Dueño: Joel]

Los valores esperados están calculados a mano a partir de un guion de 20 ticks (un mapa de 4x3,
una cosechadora y un carro): no salen del código que se prueba.
"""

import copy

import pytest

from harvest_sim.telemetria import (
    SCHEMA_VERSION,
    TraceBuilder,
    calcular_checksum,
    cargar_trace,
    con_checksum,
    escribir_trace,
    reconstruir,
    verificar_checksums,
)

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


@pytest.mark.skip(reason="pendiente — tarea 3 de Datos (métricas)")
def test_metricas_desde_el_log():
    """Las métricas del §6.2 se calculan a partir del trace.json y coinciden con las calculadas a mano."""
