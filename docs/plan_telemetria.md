# Plan de implementación — Tarea 1: telemetría y log del trace (esquema v2.0)

> **Documento personal.** Vive en `branch-joel` y **no debe llegar a `development` ni a `main`**: antes de abrir el PR se quita con `git rm docs/plan_telemetria.md` (el historial lo conserva). La guía personal (`guia_joel_datos.md`) se mantiene fuera de git. Está escrito para que lo pueda ejecutar alguien **sin más contexto que lo que se busca en la entrega del lunes**. Asume que quien lo ejecuta domina Python y las herramientas mencionadas; por eso describe qué hacer y con qué, no cómo se usa cada herramienta.

---

## 0. Contexto mínimo

- **Proyecto:** simulación 2D, en Python, de **una cosechadora y un carro recolector** en un grid pequeño. Es la **línea base reactiva** contra la que, más adelante, se compararán mejoras de coordinación (el objetivo del reto es reducir el tiempo ocioso de la cosechadora). Por eso todo debe ser simple, determinista y bien medido.
- **Entrega del lunes 16 de noviembre de 2026:** prototipo 2D funcionando de punta a punta, con telemetría, resultados de la línea base en 3 escenarios fijos, una prueba por cada regla física, un visor 2D que reproduce la corrida, gráficas y un README reproducible.
- **Qué es «telemetría» aquí:** el registro automático de lo que ocurre mientras corre la simulación (`trace.json`), y las funciones que lo arman, escriben, leen, verifican y reconstruyen. Es **la única interfaz** entre la simulación y todo lo que la lee (visor, métricas, gráficas, tests y, más adelante, Unity).

```
simulacion.py ──(cada tick)──▶ TraceBuilder ──▶ trace.json ──▶ visor (otra persona)
 registros de agentes                                      └──▶ métricas, gráficas, tests
 + eventos del mundo y del buzón
```

- **Dónde:** repo `harvest_sim/`, **rama `branch-joel`**. Fuente de verdad del formato: `docs/especificacion_primera_entrega.md` §6.1 (este plan lo resume en §2). Decisión registrada en `docs/decisiones.md` (entrada del 2026-11-15).
- **Fuera de alcance de esta tarea:** métricas y gráficas (tarea siguiente), lógica de los agentes, el mundo y el buzón (otros dueños), aleatoriedad, combustible, Unity.

## 1. Alcance y entregables

| Archivo | Qué contiene |
|---|---|
| `src/harvest_sim/telemetria.py` | `TraceBuilder`, `reconstruir`, `cargar_trace`, `escribir_trace`, `verificar_checksums` (ya existen `calcular_checksum` y `con_checksum`) |
| `tools/generar_trace_ejemplo.py` | Script determinista que genera el fixture usando `TraceBuilder` |
| `tests/fixtures/trace_ejemplo.json` | El fixture generado (se versiona junto con el script) |
| `tests/test_telemetria.py` | Pruebas de todo lo anterior (hay varios tests marcados `skip` que se activan aquí) |

No se tocan archivos de otras personas. Si falta algo en sus módulos, se pide al dueño (`docs/plan_de_trabajo.md` §1).

## 2. Contrato del archivo (resumen autocontenido)

**Estructura** (en este orden de inserción):

| Clave | Contenido |
|---|---|
| `schema_version` | `"2.0"` |
| `meta` | `{escenario, seed, total_ticks}` (`total_ticks` = último tick de la simulación) |
| `config` | Copia del config usado |
| `mundo` | `{ancho, alto, bodega, bases, grano_por_celda}` (viene de `Mundo.descripcion()`) |
| `agentes` | Arreglo de `{id, tipo, capacidad, base}` |
| `ticks` | Arreglo ordenado de `{tick, cambios, checksum}`; **solo ticks con cambios** (el 0 siempre aparece) |
| `metricas` | `{}` al construir; las llena otra tarea |

**Eventos** (`ticks[].cambios[]`, cada uno con `tipo`):

| Tipo | Campos |
|---|---|
| `AGENTE` | `id`, `set` (campos nuevos: `pose`={x,y,orientacion}, `estado`, `carga` entero, `intencion`={accion, celdas}, `objetivo`) |
| `CELDA_COSECHADA` | `celda`, `agente` |
| `DEPOSITO` | `agente`, `cantidad`, `entregado_total` |
| `MENSAJE_ENVIADO` | `id`, `tipo_mensaje`, `de`, `a`, `payload`, `entrega_en` |
| `MENSAJE_ENTREGADO` | `id`, `a` |

**Reglas:**

1. **Diferencia de agentes:** en cada tick, por cada agente, `AGENTE.set` contiene **solo los campos cuyo valor cambió** respecto al tick anterior, y cada campo va **completo** (si cambia la pose, va la pose entera). En el tick 0 van los cinco campos.
2. **Orden dentro del tick** (fijo, por categoría): `MENSAJE_ENTREGADO`, `AGENTE` (en el orden de los agentes recibido), `CELDA_COSECHADA` y `DEPOSITO` (en el orden recibido), `MENSAJE_ENVIADO`.
3. **Omisión:** si un tick no tiene ningún cambio, no aparece (salvo el 0). `meta.total_ticks` es el último tick pasado a `agregar_tick`, haya o no cambios.
4. **Checksum:** primeros 16 caracteres hexadecimales de SHA-256 sobre el JSON canónico (claves ordenadas, `separators=(",", ":")`, `ensure_ascii=False`) del objeto `{"tick", "cambios"}`. Es lo que ya hace `calcular_checksum` aplicado a un tick sin su `checksum`.
5. **Escritura reproducible:** orden de inserción fijo (**no** `sort_keys`), `indent=2`, `ensure_ascii=False`, salto de línea final (`"\n"`, también en Windows), sin fechas ni horas, solo enteros, celdas como listas.
6. **Estado en el tick `t`** = estado inicial + todos los eventos con `tick ≤ t`. Las celdas del campo (`y ≥ 1`) empiezan sin cosechar y lo entregado empieza en 0.

**Fragmento de ejemplo** (ticks 0, 7 y 8 de una corrida de 14 ticks en un mapa 4×3; se omiten los demás):

```json
{
  "schema_version": "2.0",
  "meta": {"escenario": "ejemplo_mini", "seed": 0, "total_ticks": 14},
  "config": {
    "ancho": 4,
    "alto": 3,
    "num_carros": 1,
    "num_cosechadoras": 1,
    "grano_por_celda": 1,
    "capacidad_cosechadora": 4,
    "capacidad_carro": 8,
    "tasa_transferencia": 2,
    "tasa_descarga": 4
  },
  "mundo": {"ancho": 4, "alto": 3, "bodega": [0, 0], "bases": {"carro_1": [1, 0], "cosechadora_1": [2, 0]}, "grano_por_celda": 1},
  "agentes": [
    {"id": "cosechadora_1", "tipo": "cosechadora", "capacidad": 4, "base": [2, 0]},
    {"id": "carro_1", "tipo": "carro", "capacidad": 8, "base": [1, 0]}
  ],
  "ticks": [
    {
      "tick": 0,
      "cambios": [
        {
          "tipo": "AGENTE",
          "id": "cosechadora_1",
          "set": {
            "pose": {"x": 2, "y": 0, "orientacion": "S"},
            "estado": "EN_BASE",
            "carga": 0,
            "intencion": {"accion": "NINGUNA", "celdas": []},
            "objetivo": null
          }
        },
        {
          "tipo": "AGENTE",
          "id": "carro_1",
          "set": {
            "pose": {"x": 1, "y": 0, "orientacion": "N"},
            "estado": "EN_BASE",
            "carga": 0,
            "intencion": {"accion": "NINGUNA", "celdas": []},
            "objetivo": null
          }
        }
      ],
      "checksum": "7f701082aea4e4c0"
    },
    {
      "tick": 7,
      "cambios": [
        {
          "tipo": "AGENTE",
          "id": "cosechadora_1",
          "set": {
            "pose": {"x": 3, "y": 1, "orientacion": "E"},
            "carga": 4,
            "estado": "LLENA_ESPERANDO",
            "intencion": {"accion": "ESPERAR", "celdas": []}
          }
        },
        {"tipo": "CELDA_COSECHADA", "celda": [3, 1], "agente": "cosechadora_1"},
        {
          "tipo": "MENSAJE_ENVIADO",
          "id": 1,
          "tipo_mensaje": "LLENA",
          "de": "cosechadora_1",
          "a": "carro_1",
          "payload": {"x": 3, "y": 1, "carga": 4},
          "entrega_en": 8
        }
      ],
      "checksum": "d18ba6f812482689"
    },
    {
      "tick": 8,
      "cambios": [
        {"tipo": "MENSAJE_ENTREGADO", "id": 1, "a": "carro_1"},
        {
          "tipo": "AGENTE",
          "id": "carro_1",
          "set": {"estado": "YENDO_A_COSECHADORA", "intencion": {"accion": "MOVER", "celdas": [[2, 0], [3, 0]]}, "objetivo": "cosechadora_1"}
        }
      ],
      "checksum": "9d96f3df0d98070d"
    }
  ],
  "metricas": {}
}
```

## 3. Entradas del `TraceBuilder`

Otros módulos todavía no existen o están en desarrollo, así que esta tarea se prueba con **datos de mano** que respeten estas formas (las fijó el equipo en `docs/plan_de_trabajo.md` §3):

- `TraceBuilder(config: dict, mundo: dict, agentes: list[dict])`, con `mundo = Mundo.descripcion()` y `agentes` el catálogo.
- `agregar_tick(tick, registros, eventos)` **se llama en todos los ticks**:
  - `registros`: lista con el `registro()` **completo** de cada agente, sin checksum, en el orden de los agentes: `{tick, agent_id, tipo, pose:{x,y,orientacion}, estado, carga:{actual,capacidad}, intencion:{accion,celdas}, objetivo}`. Ojo: en el registro la `carga` es `{actual, capacidad}`, pero en `AGENTE.set` es **solo el entero** `actual` (la capacidad está en `agentes`).
  - `eventos`: lista ya tipada con `buzon.drenar_eventos() + mundo.drenar_eventos()` (los cuatro tipos que no son `AGENTE`).
- `construir(metricas=None) -> dict`.

Para probar sin los demás módulos: un **guion** (lista de estados por tick) de un ciclo corto que produzca registros y eventos con estas formas. El mismo guion sirve para el fixture (T5).

## 4. Tareas

Orden recomendado: T1 → T2 → T3 → T4 (se hace en paralelo con las anteriores) → T5 → T6 → T7. T2 y T5 destraban a otras personas (Carlos usa `TraceBuilder`; Giovanni necesita el fixture).

### T1. Utilidades de archivo y verificación

- **Objetivo:** leer, escribir y verificar un `trace.json`.
- **Herramientas:** biblioteca estándar (`json`, `pathlib`), `pytest`.
- **Qué hacer:** `escribir_trace` con las reglas de escritura del §2 (crear la carpeta si no existe); `cargar_trace`; `verificar_checksums` (recalcula el checksum de cada tick con `calcular_checksum` y compara).
- **Listo cuando:** escribir dos veces el mismo trace da archivos idénticos byte a byte y `schema_version` queda como primera clave; `verificar_checksums` es `True` para un trace íntegro y `False` si se altera un valor a mano.

### T2. `TraceBuilder`

- **Objetivo:** armar el archivo tick a tick con la forma del §2.
- **Herramientas:** biblioteca estándar, `pytest`.
- **Qué hacer:** guardar config, mundo y catálogo; en cada `agregar_tick` calcular los `AGENTE` por diferencia con el tick anterior (guardando una **copia profunda** del registro anterior de cada agente, no una referencia), componer la lista de eventos con el orden por categoría, omitir el tick si queda vacío (salvo el 0), agregarle el checksum y recordar el último tick; `construir` devuelve el diccionario completo en el orden de inserción del §2.
- **Listo cuando:** pasan `test_estructura_trace_v2`, `test_ticks_sin_cambios_no_aparecen`, `test_diff_de_agente_solo_campos_que_cambian` y `test_orden_de_eventos_dentro_del_tick`.

### T3. `reconstruir`

- **Objetivo:** devolver el estado completo de cada tick, de 0 a `meta.total_ticks`, incluidos los ticks que no aparecen en el archivo.
- **Herramientas:** biblioteca estándar, `pytest`.
- **Qué hacer:** un generador que aplica los eventos en orden y, en cada tick, produce una copia del estado: por agente (`pose`, `estado`, `carga`, `intencion`, `objetivo`), celdas cosechadas, `entregado_total` y mensajes en tránsito. Si un tick no tiene eventos, repite el estado anterior.
- **Listo cuando:** pasa `test_reconstruir_estado_por_tick` y, sobre el fixture, el estado reconstruido coincide con el que generó el guion.

### T4. Pruebas

- **Objetivo:** cubrir todo lo anterior con `pytest`.
- **Qué hacer:** activar los tests `skip` de `tests/test_telemetria.py` (`test_estructura_trace_v2`, `test_ticks_sin_cambios_no_aparecen`, `test_diff_de_agente_solo_campos_que_cambian`, `test_orden_de_eventos_dentro_del_tick`, `test_reconstruir_estado_por_tick`, `test_escritura_reproducible`, `test_checksum_de_cada_tick_del_log`) y agregar los que falten. Usar el guion de §3 como entrada; valores esperados calculados a mano, no con el propio código.
- **Listo cuando:** `pytest tests/test_telemetria.py` pasa sin `skip`.

### T5. Fixture de ejemplo

- **Objetivo:** un `trace.json` de ~60 ticks, coherente con la especificación, para que el visor y las métricas se desarrollen sin esperar la simulación real.
- **Herramientas:** `tools/generar_trace_ejemplo.py` (biblioteca estándar + `TraceBuilder`).
- **Qué hacer:** definir un **guion determinista** (sin aleatoriedad) de un escenario pequeño: ambos agentes en sus bases, un ciclo completo y al menos otro que incluya **espera** (`LLENA_ESPERANDO`) y **carga parcial final**, mensajes con `id`, depósitos. Generar el JSON con `TraceBuilder` y `escribir_trace`, y guardarlo en `tests/fixtures/trace_ejemplo.json`. Verificar sobre el guion: un paso por tick (R2), agentes nunca en la misma celda (R3) y conservación de grano (R7).
- **Listo cuando:** `verificar_checksums` es `True` sobre el fixture, correr el script dos veces da el mismo archivo y quien haga el visor lo puede abrir.

### T6. Integración

- **Objetivo:** que funcione con los módulos reales cuando lleguen.
- **Qué hacer:** cuando `mundo.py`, `mensajes.py` y `simulacion.py` estén en `development`, traerlos a la rama, correr un escenario y comprobar que las formas de `registro()` y de los eventos coinciden con §3. Los ajustes de forma se piden al dueño del módulo, no se parchean aquí.
- **Listo cuando:** una corrida real produce un `trace.json` que pasa `verificar_checksums`, tiene `ticks` ordenados y es idéntico en dos corridas.

### T7. Entrega de la tarea

- **Qué hacer:** avisar a Carlos (usa `TraceBuilder`) y a Giovanni (fixture y formato), abrir PR `branch-joel → development` y esperar una aprobación (revisa Giovanni). Antes del PR, `git rm docs/plan_telemetria.md` y commit, para que no llegue a `development`.
- **Listo cuando:** el PR está integrado y CI en verde.

## 5. Orden y estimación

| Tarea | Estimación | Destraba a |
|---|---|---|
| T1 | 30–45 min | T2, T5 |
| T2 | 1–2 h | Carlos (`simulacion.py`), T3, T5 |
| T3 | 45 min | Métricas, gráficas, tests de integración |
| T4 | en paralelo | — |
| T5 | 1–2 h | Giovanni (visor) |
| T6 | cuando lleguen los módulos | Corrida real |
| T7 | 30 min | — |

## 6. Definición de terminado

- [ ] `pytest tests/test_telemetria.py` pasa, sin `skip`.
- [ ] Un trace construido cumple todas las reglas del §2 (orden, diferencias, omisión, checksum).
- [ ] Dos escrituras del mismo trace son idénticas byte a byte.
- [ ] `tests/fixtures/trace_ejemplo.json` existe, pasa `verificar_checksums` y se regenera idéntico.
- [ ] `reconstruir` cubre todos los ticks (incluidos los omitidos).
- [ ] Cualquier decisión no cubierta está en `docs/decisiones.md`.
- [ ] El PR no incluye `guia_joel_datos.md` ni este plan.

## 7. Decisiones ya tomadas (no reabrir)

`ticks` como arreglo; eventos tipados; mensajes dentro de los ticks; versión 2.0; `intencion.celdas` por tick; checksum por tick; el log guarda hechos y lo derivado ya calculado; escritura con orden de inserción fijo. Detalle y alternativas en `docs/decisiones.md` (2026-11-15). Cualquier cambio de contrato se avisa al equipo **antes** y se anota allí.

## 8. Detalles que suelen fallar

- **Referencias compartidas:** si el registro anterior se guarda sin copiar y el agente lo muta, las diferencias salen vacías.
- **Tuplas:** JSON no las distingue de listas; usar listas para celdas.
- **Solo enteros:** nada de `float` en el archivo (el checksum y los byte a byte dependen de eso).
- **Orden de agentes y eventos:** debe ser el mismo en cada tick y en cada corrida.
- **`carga`:** `{actual, capacidad}` en el registro, pero un entero en `AGENTE.set`.
- **Tick 0:** siempre aparece, con todos los campos de todos los agentes.
- **Último tick sin cambios:** `meta.total_ticks` debe reflejarlo aunque ese tick no aparezca en `ticks`.
- **Saltos de línea:** abrir el archivo con `newline="\n"` para que Windows no cambie los bytes.
- **`metricas`:** `{}` al construir; no calcularlas aquí.
