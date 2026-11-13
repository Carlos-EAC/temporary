"""Rutas: BFS y reglas de movimiento sobre el grid.  [Oswaldo]

Funciones puras (sin estado, sin importar Mundo ni agentes) para poder probarlas
solas. Mundo.vecinos y Mundo.ruta_bfs delegan aquí.

Especificación: §4.2 (conflictos de celda) y §5.2 (BFS y celda objetivo del carro).
"""

from __future__ import annotations

Celda = tuple[int, int]  # (x, y); origen arriba a la izquierda, y crece hacia abajo


def vecinos(celda: Celda, ancho: int, alto: int) -> list[Celda]:
    """Vecindad de 4 en el orden N, E, S, O, solo celdas dentro del mapa (R1, R2)."""
    raise NotImplementedError("Oswaldo: vecinos")


def bfs(origen: Celda, destino: Celda, ancho: int, alto: int, bloqueadas: set[Celda]) -> list[Celda] | None:
    """Ruta más corta, determinista (expande vecinos en orden N, E, S, O).

    Devuelve la lista de celdas SIN el origen y CON el destino; [] si origen == destino;
    None si no existe ruta. Nunca pasa por celdas de `bloqueadas`.
    """
    raise NotImplementedError("Oswaldo: bfs")


def elegir_celda_objetivo(
    origen: Celda,
    objetivo: Celda,
    ancho: int,
    alto: int,
    bloqueadas: set[Celda],
    evitar: set[Celda],
) -> Celda | None:
    """Celda vecina de `objetivo` donde se estaciona el carro (§5.2).

    Orden de decisión:
      1. Excluir celdas fuera del mapa, bloqueadas (bodega, ocupadas por otros agentes).
      2. Excluir las de `evitar` (la siguiente celda de la serpentina), salvo que sea
         la única opción.
      3. Elegir la de menor distancia BFS desde `origen`.
      4. Desempate: orden N, E, S, O.
    Devuelve None si ninguna celda es alcanzable.
    """
    raise NotImplementedError("Oswaldo: elegir_celda_objetivo")


def siguiente_paso(
    pos: Celda,
    ruta: list[Celda],
    destino: Celda,
    ancho: int,
    alto: int,
    ocupadas: set[Celda],
    bloqueadas_fijas: set[Celda],
) -> tuple[Celda | None, list[Celda]]:
    """Un paso de movimiento con resolución de conflictos (§4.2).

    - Si la siguiente celda de `ruta` está libre: devuelve (esa celda, ruta restante).
    - Si está en `ocupadas`: recalcula con BFS tratando `ocupadas | bloqueadas_fijas`
      como bloqueadas y da el primer paso de la nueva ruta.
    - Si no hay ruta: devuelve (None, ruta) -> el agente espera un tick.
    """
    raise NotImplementedError("Oswaldo: siguiente_paso")
