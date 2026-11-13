"""Corridas completas de extremo a extremo.  [Bloque D]"""

import pytest

pendiente = pytest.mark.skip(reason="pendiente — Bloque D")


@pendiente
def test_conservacion_de_grano():
    """R7: grano cosechado = en cosechadora + en carro + entregado, en CADA tick de una corrida."""


@pendiente
def test_terminacion():
    """La corrida termina y cumple las condiciones del §5.4 en los tres escenarios."""


@pendiente
def test_reproducibilidad():
    """Dos corridas del mismo escenario producen trace.json idéntico byte a byte."""
