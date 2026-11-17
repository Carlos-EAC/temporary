"""Humo del visor sin ventana.  [Dueño: Giovanni]

Idea: con SDL_VIDEODRIVER=dummy, cargar tests/fixtures/trace_ejemplo.json (lo genera Joel) y
dibujar unos cuantos cuadros sin error.
"""

import pytest


@pytest.mark.skip(reason="pendiente — Giovanni (necesita viewer.py y el fixture de Joel)")
def test_visor_dibuja_el_fixture_sin_errores():
    """Carga el trace de ejemplo y renderiza varios ticks en modo headless."""
