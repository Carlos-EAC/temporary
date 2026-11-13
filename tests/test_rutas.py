"""BFS, vecindad y resolución de conflictos de movimiento (R1, R2, §4.2).  [Dueño: Oswaldo]

Quita el `skip` de cada test al implementarlo.
"""

import pytest

pendiente = pytest.mark.skip(reason="pendiente — Oswaldo")


@pendiente
def test_movimiento_dentro_del_mapa():
    """R1: toda celda de una ruta y todo vecino están dentro del mapa."""


@pendiente
def test_movimiento_un_paso_cuatro_vecinos():
    """R2: celdas consecutivas de una ruta son vecinas de 4 (sin diagonales ni saltos)."""


@pendiente
def test_vecinos_orden_nesw():
    """vecinos() devuelve N, E, S, O en ese orden y descarta los que caen fuera del mapa."""


@pendiente
def test_bfs_ruta_mas_corta_y_determinista():
    """Misma entrada -> misma ruta; la longitud es la mínima; sin el origen y con el destino."""


@pendiente
def test_bfs_respeta_bloqueadas_y_devuelve_none():
    """No pasa por celdas bloqueadas (p. ej. la bodega, R9); sin ruta posible devuelve None."""


@pendiente
def test_bfs_origen_igual_destino():
    """Devuelve lista vacía."""


@pendiente
def test_celda_objetivo_excluye_siguiente_de_serpentina():
    """§5.2: evita la siguiente celda del camino salvo que sea la única opción."""


@pendiente
def test_celda_objetivo_desempate_nesw():
    """A igual distancia BFS, gana el orden N, E, S, O."""


@pendiente
def test_siguiente_paso_recalcula_o_espera():
    """§4.2: celda ocupada -> recalcula con BFS; sin ruta -> (None, ruta) y el agente espera."""
