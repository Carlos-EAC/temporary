"""Corridas completas de extremo a extremo.  [Dueño: Ilan]

Se marcan `skip` hasta que la simulación completa (simulacion.ejecutar) funcione;
entonces se quita el decorador. Deben pasar con los tres escenarios.
"""

import pytest

pendiente = pytest.mark.skip(reason="pendiente — espera la integración")


@pendiente
def test_no_comparten_celda():
    """R3: dos agentes nunca ocupan la misma celda, en ningún tick."""


@pendiente
def test_no_intercambian_posicion():
    """R4: dos agentes nunca intercambian posiciones entre ticks consecutivos."""


@pendiente
def test_conservacion_de_grano():
    """R7: grano cosechado = en cosechadora + en carro + entregado, en CADA tick."""


@pendiente
def test_terminacion():
    """La corrida termina y cumple las condiciones del §5.4 en los tres escenarios."""


@pendiente
def test_inicio_y_regreso_a_base():
    """Ambos agentes empiezan en su casilla de inicio y terminan en ella."""


@pendiente
def test_duracion_de_estados_en_el_log():
    """Cada tramo de TRANSFIRIENDO / DESCARGANDO dura exactamente ceil(cantidad/tasa) snapshots."""


@pendiente
def test_mensaje_pendiente_no_se_pierde():
    """Si llega LLENA con el carro ocupado, queda en la fila y el carro sale al volver a EN_BASE."""


@pendiente
def test_mensajes_viajan_al_tick_siguiente():
    """En el log, tick_entrega == tick_envio + 1 para todos los mensajes."""


@pendiente
def test_checksum_de_todo_el_log():
    """verificar_checksums(trace) es True para el log de una corrida real."""


@pendiente
def test_reproducibilidad():
    """Dos corridas del mismo escenario producen trace.json idéntico byte a byte."""


@pendiente
def test_grano_entregado_igual_al_del_campo():
    """metricas.grano_total_entregado == ancho * (alto - 1) * grano_por_celda."""
