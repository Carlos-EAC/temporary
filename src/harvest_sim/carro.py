"""Carro recolector: agente reactivo con estado.  [Bloque B]

Especificación: §5.2 (tabla de estados y transiciones).
"""

from __future__ import annotations

from enum import Enum

from .mensajes import Buzon
from .mundo import Mundo


class EstadoCarro(str, Enum):
    EN_BASE = "EN_BASE"
    YENDO_A_COSECHADORA = "YENDO_A_COSECHADORA"
    ESPERANDO_TRANSFERENCIA = "ESPERANDO_TRANSFERENCIA"
    YENDO_A_BODEGA = "YENDO_A_BODEGA"
    DESCARGANDO = "DESCARGANDO"
    REGRESANDO_A_BASE = "REGRESANDO_A_BASE"


class Carro:
    def __init__(self, agent_id: str, capacidad: int) -> None:
        self.agent_id = agent_id
        self.capacidad = capacidad
        self.estado = EstadoCarro.EN_BASE
        self.carga = 0
        # TODO (Bloque B): ruta actual, celda objetivo, contador de estado temporal, base, etc.

    def paso(self, tick: int, mundo: Mundo, buzon: Buzon) -> None:
        """Implementar la tabla del §5.2. Recordar:
        - Solo revisa su fila de entrada estando en EN_BASE (regla del carro ocupado:
          los LLENA se quedan en la fila, nunca se descartan).
        - Celda objetivo: vecina libre de la posición del mensaje; excluir bodega,
          celdas ocupadas y la siguiente celda de la serpentina (salvo única opción);
          menor distancia BFS; desempate N, E, S, O.
        - Duración de descarga = ceil(carga / tasa_descarga), calculada al entrar a DESCARGANDO.
        - Al recibir TRANSFERENCIA_TERMINADA: leer `cantidad` y registrarla.
        - Conflictos de celda: recalcular BFS con celdas ocupadas bloqueadas; si no hay
          ruta, esperar un tick (§4.2).
        """
        raise NotImplementedError("Bloque B: Carro.paso")

    def registro(self, tick: int) -> dict:
        raise NotImplementedError("Bloque B: Carro.registro")
