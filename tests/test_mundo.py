"""Mundo: layout, serpentina y movimiento de grano (R5-R9).  [Dueño: Ilan, escritos desde la especificación]

Estos tests los escribe quien NO implementa el mundo, a partir de la especificación.
Se marcan `skip` hasta que `mundo.py` entre a development; entonces se quita el decorador.
"""

import pytest

pendiente = pytest.mark.skip(reason="pendiente — espera mundo.py (Carlos)")


@pendiente
def test_casillas_de_inicio():
    """Bodega (0,0); bases de carros (1..n,0); de cosechadoras (n+1..n+m,0), con n y m genéricos."""


@pendiente
def test_serpentina_cubre_todo_el_campo():
    """El camino visita cada celda del campo (y >= 1) exactamente una vez; empieza en (0,1)."""


@pendiente
def test_serpentina_alterna_direccion():
    """Fila 1 de izquierda a derecha, fila 2 de derecha a izquierda, etc."""


@pendiente
def test_transferencia_solo_entre_vecinos():
    """R5: transferir con agentes no vecinos falla."""


@pendiente
def test_transferencia_respeta_capacidad():
    """R6: δ = min(q_cosechadora, Q_carro - q_carro); incluir caso con capacidad libre < carga."""


@pendiente
def test_celda_cosechada_una_vez():
    """R8: cosechar dos veces la misma celda no produce grano la segunda vez (o falla)."""


@pendiente
def test_cosechadora_no_entra_a_bodega():
    """R9: bloqueadas_fijas de una cosechadora incluye (0,0); la del carro no."""


@pendiente
def test_deposito_actualiza_entregado():
    """depositar() mueve la carga del carro a `entregado` y deja su carga en 0."""


@pendiente
def test_duracion_ticks():
    """ceil(cantidad / tasa), mínimo 1: (10,2)->5, (3,2)->2, (1,4)->1."""


@pendiente
def test_cosechar_registra_cambio():
    """cosechar agrega {tick, tipo: CELDA_COSECHADA, celda, agente}; depositar agrega
    {tick, tipo: DEPOSITO, agente, cantidad}; el tick es mundo.tick_actual."""


@pendiente
def test_descripcion_del_mundo():
    """descripcion() trae ancho, alto, bodega, bases (con listas, no tuplas) y grano_por_celda."""
