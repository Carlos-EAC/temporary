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
def test_registro_de_mensajes_para_el_log():
    """registro() trae id, tipo, emisor, receptor, tick_envio, tick_entrega y payload."""
