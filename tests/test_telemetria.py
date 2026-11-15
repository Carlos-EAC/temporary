"""Log v1.0, checksum y métricas.  [Bloque C]"""

import pytest

from harvest_sim.telemetria import calcular_checksum, con_checksum


def test_checksum_es_estable_e_ignora_el_campo_checksum():
    """Humo del contrato: 16 hex, independiente del orden de claves, ignora `checksum`."""
    registro = {"tick": 3, "agent_id": "carro_1", "estado": "EN_BASE"}
    c = calcular_checksum(registro)
    assert len(c) == 16 and all(ch in "0123456789abcdef" for ch in c)
    assert c == calcular_checksum({"estado": "EN_BASE", "agent_id": "carro_1", "tick": 3})
    assert c == calcular_checksum({**registro, "checksum": "otro"})
    assert con_checksum(registro)["checksum"] == c


@pytest.mark.skip(reason="pendiente — Bloque C")
def test_checksum_de_cada_tick_del_log():
    """Cada tick de un trace.json real verifica su checksum al recalcularlo."""


@pytest.mark.skip(reason="pendiente — Bloque C")
def test_metricas_desde_el_log():
    """Las métricas del §6.2 se calculan a partir del trace.json y coinciden con las de la simulación."""


@pytest.mark.skip(reason="pendiente — Joel")
def test_estructura_trace_v2():
    """El trace construido tiene schema_version 2.0, meta, config, mundo, agentes, ticks (arreglo
    ordenado) y metricas, coherentes con el config."""


@pytest.mark.skip(reason="pendiente — Joel")
def test_ticks_sin_cambios_no_aparecen():
    """Un tick sin cambios no aparece; el tick 0 siempre aparece; meta.total_ticks es el último tick."""


@pytest.mark.skip(reason="pendiente — Joel")
def test_diff_de_agente_solo_campos_que_cambian():
    """Un AGENTE.set contiene solo los campos que cambiaron y cada campo va completo."""


@pytest.mark.skip(reason="pendiente — Joel")
def test_orden_de_eventos_dentro_del_tick():
    """Orden fijo: MENSAJE_ENTREGADO, AGENTE (cosechadora y luego carro), CELDA_COSECHADA y
    DEPOSITO, MENSAJE_ENVIADO."""


@pytest.mark.skip(reason="pendiente — Joel")
def test_reconstruir_estado_por_tick():
    """reconstruir(trace) devuelve el estado de cada tick, incluidos los ticks sin cambios."""


@pytest.mark.skip(reason="pendiente — Joel")
def test_escritura_reproducible():
    """Escribir dos veces el mismo trace produce archivos idénticos; schema_version queda primero."""
