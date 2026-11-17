"""Tipos de mensaje y buzón central.  [Bloque B]

Especificación: §4.4 y §4.5. Todos los mensajes pasan por el Buzon, aunque la
comunicación sea directa; así un despachador podrá insertarse después.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TipoMensaje(str, Enum):
    LLENA = "LLENA"                                    # payload: x, y, carga
    TRANSFERENCIA_TERMINADA = "TRANSFERENCIA_TERMINADA"  # payload: cantidad


@dataclass
class Mensaje:
    tipo: TipoMensaje
    emisor: str
    receptor: str
    tick_envio: int
    payload: dict = field(default_factory=dict)
    id: int = 0  # lo asigna el Buzon al enviar (1, 2, 3, ...)


class Buzon:
    """Fila FIFO de entrada por agente. Un mensaje enviado en el tick t se lee desde t+1."""

    def enviar(self, mensaje: Mensaje) -> int:
        """Asigna un id único y creciente, encola el mensaje para entregarlo en tick+1
        y lo registra para el log. Devuelve el id."""
        raise NotImplementedError("Bloque B: Buzon.enviar")

    def entregar(self, tick: int) -> None:
        """Inicio de cada tick: pasa a los buzones de entrada los mensajes enviados en tick-1."""
        raise NotImplementedError("Bloque B: Buzon.entregar")

    def leer(self, agent_id: str) -> Mensaje | None:
        """Saca el siguiente mensaje de la fila de `agent_id` (FIFO), o None si está vacía."""
        raise NotImplementedError("Bloque B: Buzon.leer")

    def hay_pendientes(self, agent_id: str) -> bool:
        raise NotImplementedError("Bloque B: Buzon.hay_pendientes")

    def registro(self) -> list[dict]:
        """Lista de mensajes para el log: id, tipo, emisor, receptor, tick_envio,
        tick_entrega, payload."""
        raise NotImplementedError("Bloque B: Buzon.registro")
