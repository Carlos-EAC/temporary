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


class TraceBuilder:
    """Arma el trace.json durante la simulación (la usa simulacion.ejecutar).  [Joel]

    Propuesta de API; confirmar en la reunión del viernes.
    """

    def __init__(self, config: dict) -> None:
        raise NotImplementedError("Joel: TraceBuilder.__init__")

    def agregar_tick(self, tick: int, registros: list[dict]) -> None:
        """Recibe los registros de agente SIN checksum (Agente.registro) y les agrega el checksum."""
        raise NotImplementedError("Joel: TraceBuilder.agregar_tick")

    def construir(self, mensajes: list[dict], metricas: dict | None = None) -> dict:
        """Devuelve el dict completo del §6.1 (schema_version, escenario, seed, config,
        ticks, mensajes, metricas)."""
        raise NotImplementedError("Joel: TraceBuilder.construir")


def cargar_trace(ruta: str | Path) -> dict:
    """Lee un trace.json."""
    raise NotImplementedError("Joel: cargar_trace")


def verificar_checksums(trace: dict) -> bool:
    """True si el checksum de cada registro de agente coincide al recalcularlo."""
    raise NotImplementedError("Joel: verificar_checksums")


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
