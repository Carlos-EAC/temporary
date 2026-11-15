"""Log JSON v2.0 (cambios por tick), checksum, reconstrucción y métricas.  [Joel]

Especificación: §6.1. El log es la única interfaz entre la simulación y el visor, las gráficas
y (más adelante) Unity. Guarda hechos con valores nuevos explícitos y lo derivado ya calculado;
el visor no decide nada.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

from . import SCHEMA_VERSION  # noqa: F401  (se usará al construir y escribir trace.json)


def calcular_checksum(objeto: dict) -> str:
    """Primeros 16 caracteres hex de SHA-256 sobre el JSON canónico (claves ordenadas, sin
    espacios, ensure_ascii=False) del objeto SIN el campo `checksum`.

    Se usa por tick: el objeto es {"tick": t, "cambios": [...]}.
    """
    sin_checksum = {k: v for k, v in objeto.items() if k != "checksum"}
    canonico = json.dumps(sin_checksum, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()[:16]


def con_checksum(objeto: dict) -> dict:
    """Devuelve una copia del objeto con el campo `checksum` agregado al final."""
    return {**objeto, "checksum": calcular_checksum(objeto)}


class TraceBuilder:
    """Arma el trace.json durante la simulación (la usa simulacion.ejecutar).

    Propuesta de API (§3.1 del plan de trabajo):
        TraceBuilder(config, mundo, agentes)
        builder.agregar_tick(tick, registros, eventos)   # en TODOS los ticks
        builder.construir(metricas=None) -> dict
    """

    def __init__(self, config: dict, mundo: dict, agentes: list[dict]) -> None:
        """`mundo` = Mundo.descripcion(); `agentes` = catálogo estático (id, tipo, capacidad, base)."""
        raise NotImplementedError("Joel: TraceBuilder.__init__")

    def agregar_tick(self, tick: int, registros: list[dict], eventos: list[dict]) -> None:
        """Se llama en cada tick.

        - `registros`: Agente.registro() completos, SIN checksum, en el orden de los agentes.
        - `eventos`: buzon.drenar_eventos() + mundo.drenar_eventos() de ese tick.
        Calcula los eventos AGENTE por diferencia con el tick anterior (solo campos que cambian,
        cada campo completo), ordena todo por categoría (§6.1), omite el tick si no hay cambios
        (salvo el 0), agrega el checksum y recuerda `tick` como último tick (meta.total_ticks).
        """
        raise NotImplementedError("Joel: TraceBuilder.agregar_tick")

    def construir(self, metricas: dict | None = None) -> dict:
        """Devuelve el dict completo del §6.1: schema_version, meta, config, mundo, agentes,
        ticks y metricas, en ese orden de inserción."""
        raise NotImplementedError("Joel: TraceBuilder.construir")


def reconstruir(trace: dict) -> Iterator[dict]:
    """Estado completo de cada tick 0..meta.total_ticks (incluidos los ticks sin cambios),
    aplicando los eventos en orden. Lo usan las métricas, las gráficas y los tests."""
    raise NotImplementedError("Joel: reconstruir")


def cargar_trace(ruta: str | Path) -> dict:
    """Lee un trace.json."""
    raise NotImplementedError("Joel: cargar_trace")


def verificar_checksums(trace: dict) -> bool:
    """True si el checksum de cada tick coincide al recalcularlo."""
    raise NotImplementedError("Joel: verificar_checksums")


def escribir_trace(trace: dict, ruta: str | Path) -> None:
    """Escribe trace.json de forma reproducible byte a byte: orden de inserción fijo (no
    sort_keys), indent=2, ensure_ascii=False, salto de línea final, sin fechas ni horas."""
    raise NotImplementedError("Joel: escribir_trace")


def calcular_metricas(trace: dict) -> dict:
    """Calcula las métricas del §6.2 A PARTIR DEL LOG (usando `reconstruir`):
    tiempo_ocioso_cosechadora, tiempo_transfiriendo, tick_fin_cosecha,
    tiempo_completacion, distancia_cosechadora, distancia_carro, distancia_total,
    colisiones, ticks_bloqueados, num_ciclos, espera_por_ciclo, utilizacion_carro,
    grano_total_entregado. Sin combustible en esta entrega."""
    raise NotImplementedError("Joel: calcular_metricas")
