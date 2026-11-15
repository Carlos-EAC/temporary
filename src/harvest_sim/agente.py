"""Interfaz común de agente.  [Contrato — §10]"""

from __future__ import annotations

from typing import Protocol

from .mensajes import Buzon
from .mundo import Mundo


class Agente(Protocol):
    agent_id: str

    def paso(self, tick: int, mundo: Mundo, buzon: Buzon) -> None:
        """Un tick de decisión: percibir, decidir, actuar (según las tablas del §5)."""
        ...

    def registro(self, tick: int) -> dict:
        """Registro completo del agente (§6.1): tick, agent_id, tipo, pose, estado y carga
        {actual, capacidad}, sin checksum. No incluye rutas ni intenciones."""
        ...
