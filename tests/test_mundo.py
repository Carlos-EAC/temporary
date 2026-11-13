"""Reglas físicas y layout del mundo (R1, R2, R8, R9, serpentina, casillas).  [Bloque A]

Cada test está marcado como pendiente: quita el decorador al implementarlo.
"""

import pytest

pendiente = pytest.mark.skip(reason="pendiente — Bloque A")


@pendiente
def test_movimiento_dentro_del_mapa():
    """R1: todo movimiento termina en una celda dentro del mapa."""


@pendiente
def test_movimiento_un_paso_cuatro_vecinos():
    """R2: un paso por tick, en vecindad de 4 (sin diagonales ni saltos)."""


@pendiente
def test_celda_cosechada_una_vez():
    """R8: cosechar dos veces la misma celda no produce grano la segunda vez (o falla)."""


@pendiente
def test_cosechadora_no_entra_a_bodega():
    """R9: la ruta de una cosechadora nunca incluye (0,0)."""


@pendiente
def test_casillas_de_inicio():
    """Bodega (0,0); bases de carros (1..n, 0); de cosechadoras (n+1..n+m, 0), con n y m genéricos."""


@pendiente
def test_serpentina_cubre_todo_el_campo():
    """El camino visita cada celda del campo (y >= 1) exactamente una vez; empieza en (0,1)."""


@pendiente
def test_transferencia_solo_entre_vecinos():
    """R5: transferir con agentes no vecinos falla."""


@pendiente
def test_transferencia_respeta_capacidad():
    """R6: δ = min(q_cosechadora, Q_carro - q_carro); incluir caso con capacidad libre < carga."""
