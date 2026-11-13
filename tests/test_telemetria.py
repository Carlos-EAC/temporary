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
def test_checksum_de_cada_registro_del_log():
    """Cada registro de agente de un trace.json real verifica su checksum al recalcularlo."""


@pytest.mark.skip(reason="pendiente — Bloque C")
def test_metricas_desde_el_log():
    """Las métricas del §6.2 se calculan a partir del trace.json y coinciden con las de la simulación."""
