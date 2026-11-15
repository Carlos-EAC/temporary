"""Bucle de ticks y condición de término.  [Bloque B]

Especificación: §4.1 (orden del tick) y §5.4 (fin de la simulación).
"""

from __future__ import annotations

from .config import Config


def ejecutar(config: Config) -> dict:
    """Corre una simulación completa y devuelve el contenido de trace.json
    (ver telemetria.py).

    Orden de cada tick t (fijo):
      1. buzon.entregar(t)
      2. paso de la cosechadora
      3. paso del carro
      4. snapshot de ambos agentes
      5. revisar condición de término

    Además: en cada tick junta los registros de los agentes y los eventos
    (buzon.drenar_eventos() + mundo.drenar_eventos()) y se los pasa a
    TraceBuilder.agregar_tick(tick, registros, eventos); imprime por logging (§6.3) los cambios
    de estado (comparando antes/después del paso de cada agente) y los depósitos; al terminar
    llama calcular_metricas y TraceBuilder.construir.

    Termina cuando: cosechadora en FIN, carro en EN_BASE, fila de entrada del carro
    vacía, carga del carro == 0 y grano entregado == grano total del campo.
    Si se alcanza max_ticks, termina con error registrado.
    """
    raise NotImplementedError("Bloque B: ejecutar")
