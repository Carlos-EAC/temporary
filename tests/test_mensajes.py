"""Buzón y mensajes.  [Dueño: Emilio]"""

import pytest

pendiente = pytest.mark.skip(reason="pendiente — Emilio")


@pendiente
def test_fifo():
    """La fila de entrada respeta el orden de llegada."""


@pendiente
def test_ids_de_mensaje():
    """Los id son únicos y crecientes (1, 2, 3, ...) y aparecen en registro()."""


@pendiente
def test_mensaje_se_lee_al_tick_siguiente():
    """Un mensaje enviado en t no es visible en t; sí en t+1."""


@pendiente
def test_eventos_de_mensajes_para_el_log():
    """drenar_eventos() devuelve MENSAJE_ENVIADO (id, tipo_mensaje, de, a, payload, entrega_en) y
    MENSAJE_ENTREGADO (id, a) en orden, y vacía la lista."""


@pendiente
def test_log_de_consola_de_mensajes(caplog):
    """El Buzon emite un registro de log por cada envío y por cada entrega (§6.3)."""
