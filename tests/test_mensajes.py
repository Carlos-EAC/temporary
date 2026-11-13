"""Buzón y mensajes.  [Bloque B]"""

import pytest

pendiente = pytest.mark.skip(reason="pendiente — Bloque B")


@pendiente
def test_fifo():
    """La fila de entrada respeta el orden de llegada."""


@pendiente
def test_ids_de_mensaje():
    """Los id son únicos y crecientes (1, 2, 3, ...) y aparecen en el log."""


@pendiente
def test_mensaje_se_lee_al_tick_siguiente():
    """Un mensaje enviado en t no es visible en t; sí en t+1."""


@pendiente
def test_mensaje_pendiente_no_se_pierde():
    """Con el carro ocupado, el LLENA espera en la fila y el carro sale al volver a EN_BASE."""
