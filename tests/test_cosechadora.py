"""Máquina de estados de la cosechadora (§5.1).  [Dueño: Emilio]

Usa un Mundo y un Buzon falsos (clases mínimas en el propio test) para no depender de los demás.
"""

import pytest

pendiente = pytest.mark.skip(reason="pendiente — Emilio")


@pendiente
def test_cosechadora_ciclo_completo_de_estados():
    """EN_BASE -> YENDO_A_CAMPO -> COSECHANDO -> LLENA_ESPERANDO -> TRANSFIRIENDO ->
    COSECHANDO ... -> REGRESANDO_A_BASE -> FIN, con las condiciones del §5.1."""


@pendiente
def test_envia_llena_al_llenarse():
    """Al llegar carga == capacidad envía LLENA con x, y, carga y pasa a LLENA_ESPERANDO."""


@pendiente
def test_carga_parcial_final():
    """Si el campo no es múltiplo de la capacidad, la última carga parcial también envía LLENA."""


@pendiente
def test_transferencia_no_se_activa_si_el_carro_solo_pasa():
    """Carro vecino que NO está en ESPERANDO_TRANSFERENCIA no dispara la transferencia (R5)."""


@pendiente
def test_duracion_de_transferencia_depende_de_la_cantidad():
    """ceil(cantidad / tasa_transferencia) snapshots en TRANSFIRIENDO."""


@pendiente
def test_cantidad_en_mensaje_de_fin_de_transferencia():
    """TRANSFERENCIA_TERMINADA lleva `cantidad` igual a lo cedido (incluida la carga parcial)."""


@pendiente
def test_espera_si_la_siguiente_celda_esta_ocupada():
    """§4.2: no recalcula; espera un tick (intencion.accion = ESPERAR_BLOQUEO)."""


@pendiente
def test_cosechadora_registro_v1_0():
    """registro() trae pose, estado, carga, intencion{accion,celdas}, objetivo (§6.1), sin checksum."""
