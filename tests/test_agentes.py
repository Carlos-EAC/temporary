"""Comportamiento de cosechadora y carro, y reglas de conflicto.  [Bloque B]"""

import pytest

pendiente = pytest.mark.skip(reason="pendiente — Bloque B")


@pendiente
def test_no_comparten_celda():
    """R3: dos agentes nunca ocupan la misma celda, en toda una corrida."""


@pendiente
def test_no_intercambian_posicion():
    """R4: dos agentes nunca intercambian posiciones en un mismo tick."""


@pendiente
def test_conflicto_espera_o_recalcula():
    """§4.2: si la siguiente celda está ocupada, el carro recalcula o espera; la cosechadora espera."""


@pendiente
def test_carga_parcial_final():
    """Si el campo no es múltiplo de la capacidad, se atiende la última carga parcial."""


@pendiente
def test_cantidad_en_mensaje():
    """TRANSFERENCIA_TERMINADA lleva `cantidad` igual a lo cedido y coincide con la carga del carro."""


@pendiente
def test_duracion_depende_de_cantidad():
    """ceil(cantidad / tasa) en transferencia y descarga; una carga parcial dura menos."""


@pendiente
def test_duracion_estados():
    """Un estado temporal de duración N aparece en exactamente N snapshots consecutivos."""


@pendiente
def test_inicio_y_regreso_a_base():
    """Ambos agentes empiezan en su casilla de inicio y terminan en ella."""


@pendiente
def test_transferencia_no_se_activa_si_el_carro_solo_pasa():
    """Un carro vecino que no está en ESPERANDO_TRANSFERENCIA no dispara la transferencia (R5)."""
