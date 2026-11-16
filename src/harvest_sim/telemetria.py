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


def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _celda(estado: dict, agente: str) -> tuple[int, int]:
    p = estado["agentes"][agente]["pose"]
    return (p["x"], p["y"])


def series_temporales(trace: dict) -> dict[str, list]:
    """Series por tick (0..meta.total_ticks) calculadas desde el log, para graficar la evolución.

    Cada serie es una lista con un valor por tick (incluidos los ticks que no aparecen en el archivo):
    - tick: 0..total_ticks.
    - ocioso_acumulado: ticks acumulados (hasta ese tick, inclusive) con la cosechadora en LLENA_ESPERANDO.
    - distancia_cosechadora_carro: distancia Manhattan (en celdas) entre la primera cosechadora y el primer carro.
    - carga_cosechadora, carga_carro: unidades que lleva cada uno.
    - cosechado_acumulado: grano cosechado hasta ese tick (celdas cosechadas por grano_por_celda).
    - entregado_en_bodega: grano acumulado en la bodega.
    - bloqueos_acumulados: eventos BLOQUEO hasta ese tick.
    """
    cosechadoras = [a["id"] for a in trace["agentes"] if a["tipo"] == "cosechadora"]
    carros = [a["id"] for a in trace["agentes"] if a["tipo"] == "carro"]
    grano = trace["mundo"].get("grano_por_celda", 1)
    h, c = cosechadoras[0], carros[0]
    serie = {k: [] for k in ("tick", "ocioso_acumulado", "distancia_cosechadora_carro", "carga_cosechadora",
                             "carga_carro", "cosechado_acumulado", "entregado_en_bodega", "bloqueos_acumulados")}
    ocioso = bloqueos = 0
    for e in reconstruir(trace):
        ocioso += sum(1 for a in cosechadoras if e["agentes"][a]["estado"] == "LLENA_ESPERANDO")
        bloqueos += sum(1 for ev in e["eventos"] if ev["tipo"] == "BLOQUEO")
        serie["tick"].append(e["tick"])
        serie["ocioso_acumulado"].append(ocioso)
        serie["distancia_cosechadora_carro"].append(_manhattan(_celda(e, h), _celda(e, c)))
        serie["carga_cosechadora"].append(e["agentes"][h]["carga"])
        serie["carga_carro"].append(e["agentes"][c]["carga"])
        serie["cosechado_acumulado"].append(len(e["celdas_cosechadas"]) * grano)
        serie["entregado_en_bodega"].append(e["entregado_total"])
        serie["bloqueos_acumulados"].append(bloqueos)
    return serie


def calcular_metricas(trace: dict) -> dict:
    """Calcula las métricas A PARTIR DEL LOG (usa `reconstruir`; no modifica el trace).

    Definiciones (registradas en docs/decisiones.md):
    - Los ticks que se cuentan son 0..meta.total_ticks, ambos incluidos.
    - tiempo_ocioso_cosechadora: ticks con estado LLENA_ESPERANDO (suma sobre las cosechadoras).
    - tiempo_transfiriendo: ticks con estado TRANSFIRIENDO.
    - tick_fin_cosecha: tick del último MENSAJE_ENVIADO de tipo TRANSFERENCIA_TERMINADA (None si no hay).
    - tiempo_completacion: meta.total_ticks.
    - distancia_*: ticks en que la celda (x, y) del agente cambió respecto al tick anterior.
    - colisiones: ticks con dos agentes en la misma celda o intercambiando posiciones.
    - ticks_bloqueados: eventos BLOQUEO, por agente ({agent_id: n}).
    - num_ciclos: mensajes LLENA enviados.
    - espera_por_ciclo: largo de cada racha consecutiva de LLENA_ESPERANDO.
    - utilizacion_carro: ticks con el carro fuera de EN_BASE entre el total de ticks (4 decimales).
    - grano_total_entregado: entregado_total al final del log.
    Una métrica por cada variable en juego (se agregan al final, en este orden):
    - porcentaje_ocioso: ticks ociosos entre los ticks totales, en % (2 decimales).
    - ticks_por_estado: ticks que cada agente pasó en cada estado ({agent_id: {estado: n}}).
    - mensajes_enviados: mensajes enviados por tipo ({tipo_mensaje: n}).
    - distancia_cosechadora_carro_promedio / _minima / _maxima: sobre la distancia Manhattan de cada tick.
    - grano_cosechado_total, grano_esperado_total (ancho x (alto - 1) x grano_por_celda) y
      porcentaje_entregado (entregado / esperado, en %, 2 decimales; None si no se conoce el total esperado).
    """
    cosechadoras = [a["id"] for a in trace["agentes"] if a["tipo"] == "cosechadora"]
    carros = [a["id"] for a in trace["agentes"] if a["tipo"] == "carro"]
    todos = [a["id"] for a in trace["agentes"]]
    estados = list(reconstruir(trace))
    mundo = trace["mundo"]

    def celda(e, a):
        return _celda(e, a)

    def contar_estado(estado, ids):
        return sum(1 for e in estados for a in ids if e["agentes"][a]["estado"] == estado)

    espera_por_ciclo = []
    for a in cosechadoras:
        racha = 0
        for e in estados:
            if e["agentes"][a]["estado"] == "LLENA_ESPERANDO":
                racha += 1
            elif racha:
                espera_por_ciclo.append(racha)
                racha = 0
        if racha:
            espera_por_ciclo.append(racha)

    def distancia(ids):
        return sum(1 for ant, e in zip(estados, estados[1:]) for a in ids if celda(ant, a) != celda(e, a))

    colisiones = 0
    for ant, e in zip([None] + estados[:-1], estados):
        hubo = False
        for i, a in enumerate(todos):
            for b in todos[i + 1:]:
                if celda(e, a) == celda(e, b):
                    hubo = True
                elif ant and celda(ant, a) == celda(e, b) and celda(ant, b) == celda(e, a):
                    hubo = True
        colisiones += hubo

    eventos = [(e["tick"], ev) for e in estados for ev in e["eventos"]]
    terminadas = [t for t, ev in eventos
                  if ev["tipo"] == "MENSAJE_ENVIADO" and ev["tipo_mensaje"] == "TRANSFERENCIA_TERMINADA"]
    dist_h, dist_c = distancia(cosechadoras), distancia(carros)
    fuera_de_base = contar_estado("EN_BASE", carros)
    utilizacion = 0.0 if not carros else round(1 - fuera_de_base / (len(estados) * len(carros)), 4)
    ocioso = contar_estado("LLENA_ESPERANDO", cosechadoras)
    entregado = estados[-1]["entregado_total"]
    grano = mundo.get("grano_por_celda", 1)
    esperado = mundo["ancho"] * (mundo["alto"] - 1) * grano if "ancho" in mundo and "alto" in mundo else None

    ticks_por_estado = {}
    for a in todos:
        cuenta = {}
        for e in estados:
            cuenta[e["agentes"][a]["estado"]] = cuenta.get(e["agentes"][a]["estado"], 0) + 1
        ticks_por_estado[a] = cuenta
    mensajes = {}
    for _, ev in eventos:
        if ev["tipo"] == "MENSAJE_ENVIADO":
            mensajes[ev["tipo_mensaje"]] = mensajes.get(ev["tipo_mensaje"], 0) + 1
    distancias = series_temporales(trace)["distancia_cosechadora_carro"]

    return {
        "tiempo_ocioso_cosechadora": ocioso,
        "tiempo_transfiriendo": contar_estado("TRANSFIRIENDO", cosechadoras),
        "tick_fin_cosecha": max(terminadas) if terminadas else None,
        "tiempo_completacion": trace["meta"]["total_ticks"],
        "distancia_cosechadora": dist_h,
        "distancia_carro": dist_c,
        "distancia_total": dist_h + dist_c,
        "colisiones": colisiones,
        "ticks_bloqueados": {a: sum(1 for _, ev in eventos if ev["tipo"] == "BLOQUEO" and ev["agente"] == a)
                             for a in todos},
        "num_ciclos": sum(1 for _, ev in eventos
                          if ev["tipo"] == "MENSAJE_ENVIADO" and ev["tipo_mensaje"] == "LLENA"),
        "espera_por_ciclo": espera_por_ciclo,
        "utilizacion_carro": utilizacion,
        "grano_total_entregado": entregado,
        "porcentaje_ocioso": round(100 * ocioso / (len(estados) * len(cosechadoras)), 2) if cosechadoras else 0.0,
        "ticks_por_estado": ticks_por_estado,
        "mensajes_enviados": mensajes,
        "distancia_cosechadora_carro_promedio": round(sum(distancias) / len(distancias), 4),
        "distancia_cosechadora_carro_minima": min(distancias),
        "distancia_cosechadora_carro_maxima": max(distancias),
        "grano_cosechado_total": len(estados[-1]["celdas_cosechadas"]) * grano,
        "grano_esperado_total": esperado,
        "porcentaje_entregado": round(100 * entregado / esperado, 2) if esperado else None,
    }


# --- Validador del trace (contrato ejecutable del formato 2.0) -----------------------------------
_CLAVES_TRACE = ["schema_version", "meta", "config", "mundo", "agentes", "ticks", "metricas"]
_CLAVES_TICK = ["tick", "cambios", "checksum"]
_ORIENTACIONES = ("N", "E", "S", "O")
_TIPOS_AGENTE = ("cosechadora", "carro")
_CAMPOS_EVENTO = {
    "AGENTE": {"id": str, "set": dict},
    "CELDA_COSECHADA": {"celda": list, "agente": str},
    "DEPOSITO": {"agente": str, "cantidad": int, "entregado_total": int},
    "BLOQUEO": {"agente": str},
    "MENSAJE_ENVIADO": {"id": int, "tipo_mensaje": str, "de": str, "a": str, "payload": dict, "entrega_en": int},
    "MENSAJE_ENTREGADO": {"id": int, "a": str},
}


def _es_entero(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _es_celda(v) -> bool:
    return isinstance(v, list) and len(v) == 2 and all(_es_entero(c) for c in v)


def _tiene_tipo(valor, tipo) -> bool:
    return _es_entero(valor) if tipo is int else isinstance(valor, tipo)


def validar_trace(trace) -> list[str]:
    """Revisa que un trace cumpla el formato 2.0 y las reglas físicas que se pueden ver en el log.

    Devuelve la lista de errores (vacía si el trace es válido); no se detiene en el primero. Cada mensaje
    dice dónde está el problema, por ejemplo: "tick 14, evento 2 (DEPOSITO): entregado_total 7, se esperaba 6".

    Revisa: estructura (claves y su orden, versión, meta, mundo, catálogo de agentes); ticks (arreglo
    estrictamente creciente que empieza en 0, sin pasar de total_ticks, checksum correcto); eventos (tipo
    conocido, campos obligatorios y sin campos extra, tipos de dato, orden por categoría); agentes (solo
    pose, estado y carga; en el catálogo; completos en el tick 0; orientación válida; carga entre 0 y la
    capacidad; dentro del mapa); mundo (celdas dentro del campo y cosechadas una sola vez, entregado_total
    acumulado); mensajes (ids crecientes, entrega en el tick siguiente al envío y una sola vez); y las reglas
    físicas R2 (un paso por tick), R3 (dos agentes nunca en la misma celda), R4 (no intercambian posiciones)
    y R7 (grano cosechado = cargas + entregado) en cada tick.
    """
    errores: list[str] = []
    error = errores.append
    if not isinstance(trace, dict):
        return ["el trace no es un objeto JSON"]

    # --- Estructura del primer nivel ---
    claves = list(trace)
    faltan = [c for c in _CLAVES_TRACE if c not in trace]
    sobran = [c for c in claves if c not in _CLAVES_TRACE]
    if faltan:
        error(f"faltan claves en el primer nivel: {faltan}")
    if sobran:
        error(f"claves no esperadas en el primer nivel: {sobran}")
    if not faltan and not sobran and claves != _CLAVES_TRACE:
        error(f"orden de las claves del primer nivel: {claves}; se esperaba {_CLAVES_TRACE}")
    if trace.get("schema_version") != SCHEMA_VERSION:
        error(f"schema_version es {trace.get('schema_version')!r}; se esperaba {SCHEMA_VERSION!r}")

    meta = trace.get("meta")
    total = None
    if not isinstance(meta, dict):
        error("meta debe ser un objeto con escenario, seed y total_ticks")
    else:
        for c in ("escenario", "seed", "total_ticks"):
            if c not in meta:
                error(f"meta: falta {c}")
        if "total_ticks" in meta:
            if _es_entero(meta["total_ticks"]) and meta["total_ticks"] >= 0:
                total = meta["total_ticks"]
            else:
                error(f"meta: total_ticks debe ser un entero >= 0, es {meta['total_ticks']!r}")

    mundo = trace.get("mundo")
    ancho = alto = None
    grano = 1
    if not isinstance(mundo, dict):
        error("mundo debe ser un objeto")
        mundo = {}
    else:
        for c in ("ancho", "alto", "bodega", "bases", "grano_por_celda"):
            if c not in mundo:
                error(f"mundo: falta {c}")
        if _es_entero(mundo.get("ancho")) and mundo["ancho"] >= 1:
            ancho = mundo["ancho"]
        elif "ancho" in mundo:
            error(f"mundo: ancho debe ser un entero >= 1, es {mundo['ancho']!r}")
        if _es_entero(mundo.get("alto")) and mundo["alto"] >= 2:
            alto = mundo["alto"]
        elif "alto" in mundo:
            error(f"mundo: alto debe ser un entero >= 2, es {mundo['alto']!r}")
        if "bodega" in mundo and not _es_celda(mundo["bodega"]):
            error(f"mundo: bodega debe ser [x, y], es {mundo['bodega']!r}")
        if "bases" in mundo and not (isinstance(mundo["bases"], dict)
                                     and all(_es_celda(v) for v in mundo["bases"].values())):
            error("mundo: bases debe ser un objeto {agent_id: [x, y]}")
        if "grano_por_celda" in mundo:
            if _es_entero(mundo["grano_por_celda"]) and mundo["grano_por_celda"] >= 1:
                grano = mundo["grano_por_celda"]
            else:
                error(f"mundo: grano_por_celda debe ser un entero >= 1, es {mundo['grano_por_celda']!r}")

    def dentro_del_mapa(x, y):
        return ancho is None or alto is None or (0 <= x < ancho and 0 <= y < alto)

    catalogo: dict[str, dict] = {}
    agentes = trace.get("agentes")
    if not isinstance(agentes, list):
        error("agentes debe ser un arreglo")
        agentes = []
    for i, a in enumerate(agentes):
        pref = f"agentes[{i}]"
        if not isinstance(a, dict) or any(c not in a for c in ("id", "tipo", "capacidad", "base")):
            error(f"{pref}: debe tener id, tipo, capacidad y base")
            continue
        if not isinstance(a["id"], str):
            error(f"{pref}: id debe ser texto")
            continue
        if a["id"] in catalogo:
            error(f"{pref}: id repetido {a['id']!r}")
            continue
        if a["tipo"] not in _TIPOS_AGENTE:
            error(f"{pref}: tipo {a['tipo']!r} no es uno de {list(_TIPOS_AGENTE)}")
        if not (_es_entero(a["capacidad"]) and a["capacidad"] >= 1):
            error(f"{pref}: capacidad debe ser un entero >= 1, es {a['capacidad']!r}")
        if not _es_celda(a["base"]):
            error(f"{pref}: base debe ser [x, y], es {a['base']!r}")
        elif isinstance(mundo.get("bases"), dict) and mundo["bases"].get(a["id"]) not in (None, a["base"]):
            error(f"{pref}: base {a['base']} no coincide con mundo.bases ({mundo['bases'][a['id']]})")
        catalogo[a["id"]] = a

    # --- Ticks: forma, orden y checksum ---
    ticks = trace.get("ticks")
    if not isinstance(ticks, list):
        error("ticks debe ser un arreglo")
        return errores
    por_tick: dict[int, list] = {}
    anterior = None
    for i, t in enumerate(ticks):
        if not isinstance(t, dict) or list(t) != _CLAVES_TICK:
            error(f"ticks[{i}]: debe tener exactamente {_CLAVES_TICK} en ese orden")
            continue
        n = t["tick"]
        if not _es_entero(n):
            error(f"ticks[{i}]: tick debe ser un entero, es {n!r}")
            continue
        if anterior is None and n != 0:
            error(f"ticks[{i}]: el primer tick debe ser el 0, es {n}")
        if anterior is not None and n <= anterior:
            error(f"ticks[{i}]: los ticks deben ser estrictamente crecientes ({n} después de {anterior})")
            continue
        anterior = n
        if total is not None and n > total:
            error(f"tick {n}: es mayor que meta.total_ticks ({total})")
            continue
        if t["checksum"] != calcular_checksum(t):
            error(f"tick {n}: el checksum no coincide (el tick está alterado o dañado)")
        if not isinstance(t["cambios"], list):
            error(f"tick {n}: cambios debe ser un arreglo")
            continue
        por_tick[n] = t["cambios"]
    if not por_tick:
        return errores
    if total is None:
        total = max(por_tick)

    # --- Recorrido tick a tick: eventos, estado y reglas físicas ---
    estado = {a: {} for a in catalogo}
    celdas: set[tuple[int, int]] = set()
    entregado = 0
    enviados: dict[int, tuple] = {}
    entregados: set[int] = set()
    ultimo_id = 0
    posiciones_previas = None

    def agente_conocido(pref, nombre, campo="agente"):
        if nombre not in catalogo:
            error(f"{pref}: {campo} {nombre!r} no está en el catálogo de agentes")
            return False
        return True

    for tick in range(total + 1):
        ultima_categoria = -1
        agentes_en_tick: set[str] = set()
        for n, e in enumerate(por_tick.get(tick, []), 1):
            pref = f"tick {tick}, evento {n}"
            if not isinstance(e, dict):
                error(f"{pref}: el evento debe ser un objeto")
                continue
            tipo = e.get("tipo")
            if tipo not in _CAMPOS_EVENTO:
                error(f"{pref}: tipo desconocido {tipo!r}")
                continue
            pref = f"{pref} ({tipo})"
            campos = _CAMPOS_EVENTO[tipo]
            faltantes = [c for c in campos if c not in e]
            if faltantes:
                error(f"{pref}: faltan campos {faltantes}")
                continue
            extra = sorted(set(e) - {"tipo"} - set(campos))
            if extra:
                error(f"{pref}: campos no esperados {extra}")
            malos = [c for c, tp in campos.items() if not _tiene_tipo(e[c], tp)]
            if malos:
                error(f"{pref}: tipo de dato incorrecto en {malos}")
                continue
            if _CATEGORIA[tipo] < ultima_categoria:
                error(f"{pref}: fuera de orden (dentro del tick van entregas, agentes, mundo y envíos)")
            ultima_categoria = max(ultima_categoria, _CATEGORIA[tipo])

            if tipo == "AGENTE":
                ident, nuevos = e["id"], e["set"]
                if not agente_conocido(pref, ident, "id"):
                    continue
                if ident in agentes_en_tick:
                    error(f"{pref}: el agente {ident!r} aparece dos veces en el mismo tick")
                agentes_en_tick.add(ident)
                if not nuevos:
                    error(f"{pref}: set vacío")
                no_permitidos = sorted(set(nuevos) - set(_CAMPOS_AGENTE))
                if no_permitidos:
                    error(f"{pref}: campos no permitidos en set {no_permitidos} (solo pose, estado y carga)")
                if "pose" in nuevos:
                    p = nuevos["pose"]
                    if not (isinstance(p, dict) and set(p) == {"x", "y", "orientacion"}
                            and _es_entero(p["x"]) and _es_entero(p["y"])):
                        error(f"{pref}: pose debe ser {{x, y, orientacion}} con x e y enteros")
                    else:
                        if p["orientacion"] not in _ORIENTACIONES:
                            error(f"{pref}: orientacion {p['orientacion']!r} no es una de {list(_ORIENTACIONES)}")
                        if not dentro_del_mapa(p["x"], p["y"]):
                            error(f"{pref}: pose ({p['x']}, {p['y']}) fuera del mapa")
                        estado[ident]["pose"] = (p["x"], p["y"])
                if "estado" in nuevos:
                    if isinstance(nuevos["estado"], str) and nuevos["estado"]:
                        estado[ident]["estado"] = nuevos["estado"]
                    else:
                        error(f"{pref}: estado debe ser texto no vacío")
                if "carga" in nuevos:
                    c, cap = nuevos["carga"], catalogo[ident].get("capacidad")
                    if not _es_entero(c) or c < 0 or (_es_entero(cap) and c > cap):
                        error(f"{pref}: carga {c!r} debe ser un entero entre 0 y la capacidad ({cap})")
                    else:
                        estado[ident]["carga"] = c

            elif tipo == "CELDA_COSECHADA":
                agente_conocido(pref, e["agente"])
                if not _es_celda(e["celda"]):
                    error(f"{pref}: celda debe ser [x, y]")
                    continue
                x, y = e["celda"]
                if not (dentro_del_mapa(x, y) and y >= 1):
                    error(f"{pref}: celda ({x}, {y}) fuera del campo (el campo son las filas y >= 1)")
                if (x, y) in celdas:
                    error(f"{pref}: la celda ({x}, {y}) se cosecha dos veces")
                celdas.add((x, y))

            elif tipo == "DEPOSITO":
                agente_conocido(pref, e["agente"])
                if e["cantidad"] < 0:
                    error(f"{pref}: cantidad negativa ({e['cantidad']})")
                esperado = entregado + e["cantidad"]
                if e["entregado_total"] != esperado:
                    error(f"{pref}: entregado_total {e['entregado_total']}, se esperaba {esperado}")
                entregado = e["entregado_total"]

            elif tipo == "BLOQUEO":
                agente_conocido(pref, e["agente"])

            elif tipo == "MENSAJE_ENVIADO":
                agente_conocido(pref, e["de"], "de")
                agente_conocido(pref, e["a"], "a")
                if e["id"] in enviados:
                    error(f"{pref}: id {e['id']} repetido")
                elif e["id"] <= ultimo_id:
                    error(f"{pref}: id {e['id']} no es creciente (el anterior fue {ultimo_id})")
                if e["entrega_en"] != tick + 1:
                    error(f"{pref}: entrega_en {e['entrega_en']}, se esperaba {tick + 1} (el tick siguiente)")
                enviados.setdefault(e["id"], (tick, e["a"], e["entrega_en"]))
                ultimo_id = max(ultimo_id, e["id"])

            elif tipo == "MENSAJE_ENTREGADO":
                if e["id"] not in enviados:
                    error(f"{pref}: el mensaje {e['id']} no corresponde a un envío previo")
                    continue
                _, destinatario, entrega_en = enviados[e["id"]]
                if e["id"] in entregados:
                    error(f"{pref}: el mensaje {e['id']} se entrega dos veces")
                if tick != entrega_en:
                    error(f"{pref}: el mensaje {e['id']} se entrega en el tick {tick}, se esperaba {entrega_en}")
                if e["a"] != destinatario:
                    error(f"{pref}: el mensaje {e['id']} se entrega a {e['a']!r} pero se envió a {destinatario!r}")
                entregados.add(e["id"])

        if tick == 0:
            for a, campos_a in estado.items():
                ausentes = [c for c in _CAMPOS_AGENTE if c not in campos_a]
                if ausentes:
                    error(f"tick 0: al agente {a!r} le faltan {ausentes} (el tick 0 es el estado inicial completo)")

        # Reglas físicas: solo si todos los agentes tienen estado completo
        if not catalogo or any(any(c not in s for c in _CAMPOS_AGENTE) for s in estado.values()):
            continue
        posiciones = {a: s["pose"] for a, s in estado.items()}
        nombres = list(posiciones)
        for i, a in enumerate(nombres):
            for b in nombres[i + 1:]:
                if posiciones[a] == posiciones[b]:
                    error(f"tick {tick}: R3, {a} y {b} ocupan la misma celda {posiciones[a]}")
                elif (posiciones_previas and posiciones_previas[a] == posiciones[b]
                      and posiciones_previas[b] == posiciones[a]):
                    error(f"tick {tick}: R4, {a} y {b} intercambian posiciones")
        if posiciones_previas:
            for a in nombres:
                if _manhattan(posiciones_previas[a], posiciones[a]) > 1:
                    error(f"tick {tick}: R2, {a} se mueve de {posiciones_previas[a]} a {posiciones[a]} "
                          "(más de una celda)")
        cosechado = len(celdas) * grano
        en_agentes = sum(s["carga"] for s in estado.values())
        if cosechado != en_agentes + entregado:
            error(f"tick {tick}: R7, grano cosechado {cosechado} distinto de cargas {en_agentes} "
                  f"+ entregado {entregado}")
        posiciones_previas = posiciones

    for ident, (enviado_en, _, entrega_en) in sorted(enviados.items()):
        if ident not in entregados and entrega_en <= total:
            error(f"el mensaje {ident} (enviado en el tick {enviado_en}) nunca se entregó")
    return errores
