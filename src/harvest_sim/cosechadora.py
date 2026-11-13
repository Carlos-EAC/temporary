"""Cosechadora: agente reactivo con estado.  [Bloque B]

Especificación: §5.1 (tabla de estados y transiciones). Camino fijo: serpentina.
"""

from __future__ import annotations

from enum import Enum

from .mensajes import Buzon
from .mundo import Mundo


class EstadoCosechadora(str, Enum):
    EN_BASE = "EN_BASE"
    YENDO_A_CAMPO = "YENDO_A_CAMPO"
    COSECHANDO = "COSECHANDO"
    LLENA_ESPERANDO = "LLENA_ESPERANDO"
    TRANSFIRIENDO = "TRANSFIRIENDO"
    REGRESANDO_A_BASE = "REGRESANDO_A_BASE"
    FIN = "FIN"


class Cosechadora:
    def __init__(self, agent_id: str, capacidad: int) -> None:
        self.agent_id = agent_id
        self.capacidad = capacidad
        self.estado = EstadoCosechadora.EN_BASE
        self.carga = 0
        # TODO (Bloque B): índice en el camino, contador de estado temporal, base, etc.

    def paso(self, tick: int, mundo: Mundo, buzon: Buzon) -> None:
        """Implementar la tabla del §5.1. Recordar:
        - Evaluación de carga tras cosechar: enviar LLENA si carga == capacidad o si fue
          la última celda del camino (carga parcial).
        - Iniciar la transferencia solo si el carro está vecino Y en ESPERANDO_TRANSFERENCIA.
        - Duración = ceil(cantidad / tasa_transferencia), calculada al entrar a TRANSFIRIENDO.
        - Al salir de TRANSFIRIENDO: mundo.transferir(...) y enviar TRANSFERENCIA_TERMINADA
          con `cantidad`.
        - Conflictos de celda: espera si la siguiente celda del camino está ocupada (§4.2).
        """
        raise NotImplementedError("Bloque B: Cosechadora.paso")

    def registro(self, tick: int) -> dict:
        raise NotImplementedError("Bloque B: Cosechadora.registro")
