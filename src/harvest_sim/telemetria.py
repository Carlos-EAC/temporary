"""Log JSON v1.0, checksum y métricas.  [Bloque C]

Especificación: §6. El log es la única interfaz entre la simulación y el visor,
las gráficas (y, más adelante, Unity).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import SCHEMA_VERSION  # noqa: F401  (se usará al escribir trace.json)


def calcular_checksum(registro: dict) -> str:
    """Primeros 16 caracteres hex de SHA-256 sobre el JSON canónico (claves
    ordenadas, sin espacios) del registro SIN el campo `checksum`."""
    sin_checksum = {k: v for k, v in registro.items() if k != "checksum"}
    canonico = json.dumps(sin_checksum, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()[:16]


def con_checksum(registro: dict) -> dict:
    """Devuelve una copia del registro con el campo `checksum` agregado."""
    return {**registro, "checksum": calcular_checksum(registro)}


def escribir_trace(trace: dict, ruta: str | Path) -> None:
    """TODO (Bloque C): escribir trace.json de forma reproducible byte a byte
    (claves en orden estable, mismo formato siempre)."""
    raise NotImplementedError("Bloque C: escribir_trace")


def calcular_metricas(trace: dict) -> dict:
    """TODO (Bloque C): calcular las métricas del §6.2 A PARTIR DEL LOG:
    tiempo_ocioso_cosechadora, tiempo_transfiriendo, tick_fin_cosecha,
    tiempo_completacion, distancia_cosechadora, distancia_carro, distancia_total,
    colisiones, ticks_bloqueados, num_ciclos, espera_por_ciclo, utilizacion_carro,
    grano_total_entregado. Sin combustible en esta entrega."""
    raise NotImplementedError("Bloque C: calcular_metricas")
