"""Grid, bodega, bases, serpentina, BFS y movimiento de grano.  [Bloque A]

Especificación: §2 (mundo y reglas R1-R9) y §4.2 (conflictos de celda).

El grano solo cambia de manos mediante funciones de este módulo (cosechar,
transferir, depositar), para que R6, R7 y R8 se verifiquen en un solo lugar.
"""

from __future__ import annotations

from .config import Config

Celda = tuple[int, int]  # (x, y); origen arriba a la izquierda, y crece hacia abajo


class Mundo:
    """Estado físico del mundo. Los agentes lo consultan; no se leen entre sí."""

    bodega: Celda = (0, 0)

    def __init__(self, config: Config) -> None:
        """TODO (Bloque A): construir el grid y calcular las casillas de la fila 0
        con n = num_carros y m = num_cosechadoras genéricos (NO escribir (1,0) ni
        (2,0) a mano):
          (0,0)            bodega
          (i,0), 1..n      base del carro i
          (n+j,0), 1..m    base de la cosechadora j
        """
        raise NotImplementedError("Bloque A: Mundo.__init__")

    # --- Layout ---------------------------------------------------------
    def base_de(self, agent_id: str) -> Celda:
        raise NotImplementedError("Bloque A: Mundo.base_de")

    def camino_serpentina(self) -> list[Celda]:
        """Filas y=1..alto-1; fila 1 de izquierda a derecha, fila 2 de derecha a
        izquierda, etc. Empieza en (0, 1). Cubre cada celda del campo una vez."""
        raise NotImplementedError("Bloque A: Mundo.camino_serpentina")

    def vecinos(self, celda: Celda) -> list[Celda]:
        """Vecindad de 4 en el orden N, E, S, O, dentro del mapa."""
        raise NotImplementedError("Bloque A: Mundo.vecinos")

    # --- Percepción -----------------------------------------------------
    def posicion(self, agent_id: str) -> Celda:
        raise NotImplementedError("Bloque A: Mundo.posicion")

    def estado_de(self, agent_id: str) -> str:
        """Estado actual de otro agente (percepción directa, §5.1)."""
        raise NotImplementedError("Bloque A: Mundo.estado_de")

    # --- Rutas ----------------------------------------------------------
    def ruta_bfs(self, origen: Celda, destino: Celda, bloqueadas: set[Celda]) -> list[Celda] | None:
        """BFS determinista (vecinos en orden N, E, S, O). Devuelve la lista de celdas
        desde el siguiente paso hasta el destino, o None si no hay ruta.
        La bodega está siempre bloqueada para las cosechadoras (R9)."""
        raise NotImplementedError("Bloque A: Mundo.ruta_bfs")

    # --- Grano ----------------------------------------------------------
    def cosechar(self, agent_id: str, celda: Celda) -> int:
        """Cosecha la celda (R8: solo una vez). Devuelve las unidades cosechadas."""
        raise NotImplementedError("Bloque A: Mundo.cosechar")

    def transferir(self, de: str, a: str, cantidad: int) -> int:
        """Transferencia atómica. Devuelve δ = min(cantidad, capacidad libre del receptor) (R6).
        Exige agentes en celdas vecinas (R5)."""
        raise NotImplementedError("Bloque A: Mundo.transferir")

    def depositar(self, agent_id: str) -> int:
        """Entrega la carga del agente a la bodega. Devuelve las unidades depositadas."""
        raise NotImplementedError("Bloque A: Mundo.depositar")
