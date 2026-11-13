"""Máquina de estados del carro (§5.2).  [Dueño: Oswaldo]

Usa un Mundo y un Buzon falsos (clases mínimas en el propio test) para no depender de los demás.
"""

import pytest

pendiente = pytest.mark.skip(reason="pendiente — Oswaldo")


@pendiente
def test_carro_solo_revisa_su_fila_en_en_base():
    """Con mensajes en la fila y estado distinto de EN_BASE, no los toca ni los descarta."""


@pendiente
def test_carro_atiende_en_orden_fifo():
    """Con dos LLENA pendientes, atiende primero el más antiguo."""


@pendiente
def test_carro_ciclo_completo_de_estados():
    """EN_BASE -> YENDO_A_COSECHADORA -> ESPERANDO_TRANSFERENCIA -> YENDO_A_BODEGA ->
    DESCARGANDO -> REGRESANDO_A_BASE -> EN_BASE, con las condiciones del §5.2."""


@pendiente
def test_carro_duracion_de_descarga():
    """ceil(carga / tasa_descarga) snapshots en DESCARGANDO; una carga parcial dura menos."""


@pendiente
def test_carro_registra_cantidad_del_mensaje():
    """Al recibir TRANSFERENCIA_TERMINADA lee `cantidad` y coincide con su carga."""


@pendiente
def test_carro_registro_v1_0():
    """registro() trae pose, estado, carga, intencion{accion,celdas}, objetivo (§6.1), sin checksum."""
