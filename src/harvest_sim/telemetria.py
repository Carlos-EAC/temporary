"""Log JSON v2.0 (cambios por tick), checksum, reconstrucción y métricas.  [Joel]

El log es la única interfaz entre la simulación y el visor, las gráficas y (más adelante) Unity.
Guarda solo cambios explícitos (pose, estado y carga de los agentes, celdas cosechadas,
depósitos, bloqueos y mensajes) y todo lo derivado ya calculado. No guarda rutas ni
intenciones: dependen del algoritmo del agente y el visor no debe interpretarlas.

Formato (esquema 2.0):
    schema_version, meta, config, mundo, agentes, ticks, metricas
    ticks = arreglo ordenado de {tick, cambios, checksum}; solo ticks con cambios (el 0 siempre).
    cambios = lista de eventos tipados, en orden fijo por categoría:
        MENSAJE_ENTREGADO, AGENTE, (CELDA_COSECHADA | DEPOSITO | BLOQUEO), MENSAJE_ENVIADO
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

SCHEMA_VERSION = "2.0"

# Campos del registro de un agente que el log sigue; cualquier otro campo se ignora.
_CAMPOS_AGENTE = ("pose", "estado", "carga")

# Categoría de cada tipo de evento: define el orden dentro del tick (estable dentro de la categoría).
_CATEGORIA = {
    "MENSAJE_ENTREGADO": 0,
    "AGENTE": 1,
    "CELDA_COSECHADA": 2,
    "DEPOSITO": 2,
    "BLOQUEO": 2,
    "MENSAJE_ENVIADO": 3,
}

_AUSENTE = object()


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

        TraceBuilder(config, mundo, agentes)
        builder.agregar_tick(tick, registros, eventos)   # en TODOS los ticks, en orden
        builder.construir(metricas=None) -> dict
    """

    def __init__(self, config: dict, mundo: dict, agentes: list[dict]) -> None:
        """`mundo` = Mundo.descripcion(); `agentes` = catálogo estático (id, tipo, capacidad, base)."""
        self._config = copy.deepcopy(config)
        self._mundo = copy.deepcopy(mundo)
        self._agentes = copy.deepcopy(agentes)
        self._ticks: list[dict] = []
        self._previo: dict[str, dict] = {}
        self._ultimo_tick: int | None = None

    def agregar_tick(self, tick: int, registros: list[dict], eventos: list[dict]) -> None:
        """Se llama en cada tick, con ticks estrictamente crecientes.

        - `registros`: Agente.registro() completos, SIN checksum, en el orden de los agentes.
        - `eventos`: los eventos del tick que no son AGENTE (celdas, depósitos, bloqueos, mensajes).
        Calcula los eventos AGENTE por diferencia con el tick anterior (solo los campos pose,
        estado y carga que cambian, cada campo completo), ordena todo por categoría, omite el tick
        si no hay cambios (salvo el 0) y le agrega el checksum.
        """
        if self._ultimo_tick is not None and tick <= self._ultimo_tick:
            raise ValueError(f"los ticks deben ser crecientes: {tick} después de {self._ultimo_tick}")

        for e in eventos:
            tipo = e.get("tipo")
            if tipo not in _CATEGORIA or tipo == "AGENTE":
                raise ValueError(f"tipo de evento no válido en `eventos`: {tipo!r}")

        cambios_agentes = []
        for r in registros:
            actual = {
                "pose": copy.deepcopy(r["pose"]),
                "estado": r["estado"],
                "carga": r["carga"]["actual"],
            }
            previo = self._previo.get(r["agent_id"], {})
            nuevos = {c: actual[c] for c in _CAMPOS_AGENTE if previo.get(c, _AUSENTE) != actual[c]}
            if nuevos:
                cambios_agentes.append({"tipo": "AGENTE", "id": r["agent_id"], "set": nuevos})
            self._previo[r["agent_id"]] = actual  # copia propia: el agente puede mutar su registro

        cambios = sorted(
            copy.deepcopy(eventos) + cambios_agentes,
            key=lambda e: _CATEGORIA[e["tipo"]],
        )
        if cambios or tick == 0:
            self._ticks.append(con_checksum({"tick": tick, "cambios": cambios}))
        self._ultimo_tick = tick

    def construir(self, metricas: dict | None = None) -> dict:
        """Devuelve el dict completo: schema_version, meta, config, mundo, agentes, ticks y
        metricas, en ese orden de inserción."""
        if self._ultimo_tick is None:
            raise ValueError("no hay ticks: llama a agregar_tick antes de construir")
        return {
            "schema_version": SCHEMA_VERSION,
            "meta": {
                "escenario": self._config.get("nombre"),
                "seed": self._config.get("seed"),
                "total_ticks": self._ultimo_tick,
            },
            "config": copy.deepcopy(self._config),
            "mundo": copy.deepcopy(self._mundo),
            "agentes": copy.deepcopy(self._agentes),
            "ticks": copy.deepcopy(self._ticks),
            "metricas": {} if metricas is None else copy.deepcopy(metricas),
        }


def reconstruir(trace: dict) -> Iterator[dict]:
    """Estado completo de cada tick 0..meta.total_ticks (incluidos los ticks sin cambios),
    aplicando los eventos en orden. Lo usan las métricas, las gráficas y los tests.

    Cada elemento es una copia independiente:
        {"tick": t,
         "agentes": {id: {"pose", "estado", "carga"}},
         "celdas_cosechadas": [[x, y], ...],      # en el orden en que se cosecharon
         "entregado_total": n,
         "mensajes_en_transito": [id, ...],       # enviados y aún no entregados
         "eventos": [...]}                        # los eventos de ese tick ([] si se omitió)
    """
    total = trace["meta"]["total_ticks"]
    ticks = trace["ticks"]
    anterior = -1
    for t in ticks:
        if t["tick"] <= anterior or t["tick"] > total:
            raise ValueError(f"ticks fuera de orden o mayores que total_ticks: {t['tick']}")
        anterior = t["tick"]

    agentes: dict[str, dict] = {}
    celdas: list[list[int]] = []
    entregado = 0
    en_transito: list[int] = []
    i = 0
    for tick in range(total + 1):
        eventos: list[dict] = []
        if i < len(ticks) and ticks[i]["tick"] == tick:
            eventos = ticks[i]["cambios"]
            i += 1
        for e in eventos:
            tipo = e["tipo"]
            if tipo == "AGENTE":
                agentes.setdefault(e["id"], {}).update(copy.deepcopy(e["set"]))
            elif tipo == "CELDA_COSECHADA":
                celdas.append(list(e["celda"]))
            elif tipo == "DEPOSITO":
                entregado = e["entregado_total"]
            elif tipo == "MENSAJE_ENVIADO":
                en_transito.append(e["id"])
            elif tipo == "MENSAJE_ENTREGADO":
                if e["id"] in en_transito:
                    en_transito.remove(e["id"])
            # BLOQUEO no cambia el estado: solo queda en `eventos` para las métricas
        yield {
            "tick": tick,
            "agentes": copy.deepcopy(agentes),
            "celdas_cosechadas": copy.deepcopy(celdas),
            "entregado_total": entregado,
            "mensajes_en_transito": list(en_transito),
            "eventos": copy.deepcopy(eventos),
        }


def cargar_trace(ruta: str | Path) -> dict:
    """Lee un trace.json."""
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def verificar_checksums(trace: dict) -> bool:
    """True si el checksum de cada tick coincide al recalcularlo."""
    return all(t.get("checksum") == calcular_checksum(t) for t in trace["ticks"])


def escribir_trace(trace: dict, ruta: str | Path) -> None:
    """Escribe trace.json de forma reproducible byte a byte: orden de inserción fijo (no
    sort_keys), indent=2, ensure_ascii=False, salto de línea final, sin fechas ni horas."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(trace, indent=2, ensure_ascii=False) + "\n"
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)


def calcular_metricas(trace: dict) -> dict:
    """Calcula las métricas del §6.2 A PARTIR DEL LOG (usando `reconstruir`).
    Pendiente: es la tarea 3 de Datos (después del trace y del fixture)."""
    raise NotImplementedError("Joel: calcular_metricas")
