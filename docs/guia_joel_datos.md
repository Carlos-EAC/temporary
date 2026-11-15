# Guía de la parte de Datos (Joel)

Esta guía explica **qué es** tu parte, **para qué sirve**, **qué hacer y en qué orden**, y **cómo comprobar que vas bien**. Complementa el plan ([`plan_de_trabajo.md`](plan_de_trabajo.md)) y la especificación (§6 y §7 de [`especificacion_primera_entrega.md`](especificacion_primera_entrega.md)).

---

## 1. Tu parte en una frase

**Eres el dueño del registro de la simulación (el log) y de convertirlo en números y gráficas.**

La simulación es una película que Python "graba" tick por tick en un archivo (`trace.json`). Tú decides **qué se graba y en qué formato**, compruebas que la grabación es fiel, y luego la **analizas**: calculas las métricas y haces las gráficas que dicen si una versión del sistema es mejor que otra.

```
Python simula ──▶ trace.json ──▶ visor (Giovanni)
                      │
                      └────────▶ tus métricas y gráficas
```

Es la parte con la que se **demuestra** el resultado del reto. El objetivo del proyecto es "reducir el tiempo ocioso de la cosechadora frente a una línea base". Alguien tiene que medir ese tiempo ocioso de forma confiable. Eres tú.

---

## 2. Por qué importa (para la rúbrica y para el reto)

| Qué haces | Por qué se evalúa |
|---|---|
| Esquema del log con versión y checksum | Criterio de **arquitectura de software**: interfaz con esquema versionado, logs, reproducibilidad |
| Que dos corridas den el mismo archivo | **Reproducibilidad** (sin ella, el resultado se considera no verificable) |
| Métricas calculadas desde el log | **Simulación** y **algoritmos**: la línea base debe estar medida en escenarios fijos |
| Gráficas y tabla de los tres escenarios | **Reflexión** con datos: "no afirmaciones genéricas", sino números de los logs |
| El log como único puente hacia el visor (y Unity después) | La propuesta dice que Python es la fuente de verdad y Unity solo visualiza |

---

## 3. Vocabulario que necesitas

| Término | Significa aquí |
|---|---|
| **Tick** | Un paso de tiempo de la simulación (0, 1, 2, …) |
| **Snapshot** | La foto del estado de los agentes al final de un tick |
| **Log / trace** | El archivo `trace.json` con todos los snapshots y los mensajes |
| **Checksum** | Una "huella" de cada registro; si alguien lo edita o se daña, la huella ya no coincide |
| **Determinista** | Mismo config → exactamente el mismo resultado, siempre |
| **Métrica** | Un número que resume la corrida (p. ej. "ticks que la cosechadora esperó") |
| **Línea base** | La versión simple (carro reactivo) contra la que se compararán las mejoras. Tus números son lo que hay que superar |
| **Fixture** | Un archivo de datos de ejemplo fijo para probar sin depender del código real |

---

## 4. Cómo se ve un `trace.json`

Lee primero el §6.1 de la especificación. En pequeño, así es la idea (recortado):

```json
{
  "schema_version": "1.0",
  "escenario": "escenario_a",
  "seed": 0,
  "config": { "ancho": 8, "alto": 7, "capacidad_cosechadora": 10 },
  "ticks": [
    { "tick": 0, "agentes": [
        { "tick": 0, "agent_id": "cosechadora_1", "tipo": "cosechadora",
          "pose": {"x": 2, "y": 0, "orientacion": "S"}, "estado": "EN_BASE",
          "carga": {"actual": 0, "capacidad": 10},
          "intencion": {"accion": "NINGUNA", "celdas": []}, "objetivo": null,
          "checksum": "9f2c1a7d3b0e4a55" },
        { "tick": 0, "agent_id": "carro_1", "...": "..." }
    ]},
    { "tick": 1, "agentes": [ "..." ] }
  ],
  "mensajes": [
    { "id": 1, "tipo": "LLENA", "emisor": "cosechadora_1", "receptor": "carro_1",
      "tick_envio": 14, "tick_entrega": 15, "payload": {"x": 5, "y": 2, "carga": 10} }
  ],
  "metricas": { "tiempo_ocioso_cosechadora": 12 }
}
```

Cada tick tiene **un registro por agente** y cada registro lleva su checksum. Los mensajes van en una lista aparte.

---

## 5. Tus 5 tareas, en orden

| # | Tarea | Archivo | Para quién es urgente | Tiempo aprox. |
|---|---|---|---|---|
| 1 | Fixture de ejemplo | `tools/generar_trace_ejemplo.py` → `tests/fixtures/trace_ejemplo.json` | **Giovanni** (dibuja el visor con él) y tú | 1–2 h |
| 2 | Constructor, lectura, escritura y verificación del log | `src/harvest_sim/telemetria.py` | **Carlos** (lo usa en `simulacion.py`) | 1–2 h |
| 3 | Métricas desde el log | `telemetria.py` (`calcular_metricas`) | Todos, el domingo | 2–3 h |
| 4 | Gráficas y tabla comparativa | `viz/plots.py` | Entrega | 2–3 h |
| 5 | Corridas reales y análisis | — | Entrega | domingo |

Las tareas 1 y 2 son las que **destraban a otros**: hazlas primero. Las 3 y 4 las puedes desarrollar sobre el fixture, sin esperar a la simulación real.

### Tus primeros 30 minutos

```bash
cd harvest_sim
git switch branch-joel
git merge origin/development
source .venv/bin/activate          # o crea el entorno (ver README)
pytest tests/test_telemetria.py    # debe pasar el único test activo
```

Luego: lee §6 de la especificación, abre `src/harvest_sim/telemetria.py` (ya tienes implementados `calcular_checksum` y `con_checksum`) y crea `tools/generar_trace_ejemplo.py`.

---

## 6. Tarea 1 — El fixture de ejemplo

**Qué es:** un `trace.json` pequeño, inventado a mano pero **coherente con las reglas** de la especificación. No viene de la simulación real (que aún no existe).

**Qué guarda el formato (y qué no).** Cada tick guarda, por cada agente: su **posición** (`pose`: x, y y orientación), su **estado** (`estado`), su **carga** (`actual` y `capacidad`), su **intención** (la siguiente acción y las próximas celdas) y su **objetivo**; y aparte, la lista de **mensajes** entre agentes. El **entorno no se guarda tick por tick**: el tamaño del grid y la ubicación de la bodega y las bases salen de `config`, y qué celdas ya se cosecharon se **deduce** de por dónde ha pasado la cosechadora cosechando. Así el log es más pequeño y hay una sola fuente de verdad. Si el visor necesitara el mapa de celdas cosechadas ya calculado, se agregaría al log, no al visor.

**¿Script fijo o valores aleatorios?** Un **script determinista, sin aleatoriedad**. Razones:
- El proyecto deja la incertidumbre fuera del alcance, y la reproducibilidad es parte de la rúbrica.
- Un fixture que cambia en cada corrida hace que los tests "fallen a veces" y no podrías calcular a mano los resultados esperados.
- "Hardcodeado" no significa escribir cada tick a mano: significa que el **guion** (qué hace cada agente por tramos) está fijo en el script y un bucle genera los ticks. Se versionan el script y el JSON que genera.

**Para qué sirve:**
- Giovanni dibuja el visor leyendo un archivo real.
- Tú desarrollas métricas y gráficas con datos que **puedes verificar a mano**.
- Los tests de `telemetria` tienen datos conocidos contra los cuales comparar.

**Cómo hacerlo** (no es "escribir 60 ticks a mano": se genera con un script).

1. Elige un escenario muy chico, por ejemplo `ancho=4`, `alto=3`, capacidad de la cosechadora 4, capacidad del carro 8. Así los ciclos son cortos y puedes seguirlos con el dedo.
2. Escribe el "guion" de lo que pasa, por tramos, con funciones auxiliares:

   | Tramo | Cosechadora | Carro |
   |---|---|---|
   | Inicio | `EN_BASE` en su casilla, carga 0 | `EN_BASE` en su casilla |
   | Va al campo | `YENDO_A_CAMPO`, se mueve una celda por tick | `EN_BASE` quieto |
   | Cosecha | `COSECHANDO`, se mueve y la carga sube de 1 en 1 | `EN_BASE` quieto |
   | Se llena | `LLENA_ESPERANDO`, quieta, carga 4. **Mensaje `LLENA`** | recibe el mensaje al tick siguiente y sale |
   | Espera | quieta (esto es el tiempo ocioso) | `YENDO_A_COSECHADORA`, una celda por tick |
   | Transfiere | `TRANSFIRIENDO` durante `ceil(4/tasa)` ticks | `ESPERANDO_TRANSFERENCIA` |
   | Termina | carga 0, **mensaje `TRANSFERENCIA_TERMINADA`** con `cantidad: 4` | carga 4, `YENDO_A_BODEGA` |
   | Descarga | sigue cosechando | `DESCARGANDO`, luego `REGRESANDO_A_BASE`, `EN_BASE` |

3. Escribe una función como `registro(tick, agent_id, ...)` que arme el diccionario del §3.2 del plan (pose, estado, carga, intención, objetivo) y pásalo por `con_checksum`.
4. Recorre los ticks con un bucle y arma la lista. Los mensajes llevan `id` creciente y `tick_entrega = tick_envio + 1`.
5. Guarda el JSON con `json.dump(..., sort_keys=True, indent=2, ensure_ascii=False)`.

**Qué debe tener el fixture (mínimo):** un ciclo completo, **al menos un tick de espera** (`LLENA_ESPERANDO`), una carga parcial al final, un par de mensajes y el regreso de ambos a su base.

**Cómo saber que está bien:**
- Las celdas de cada agente cambian de un tick al siguiente como máximo una unidad en x **o** en y (R2).
- Los agentes nunca comparten celda (R3).
- La suma `cosechado = en cosechadora + en carro + entregado` se mantiene en cada tick (R7).
- Cuando termines la tarea 2, `verificar_checksums(trace)` da `True`.

**Pide a Giovanni** que lo abra apenas lo subas a `development`. Si algo le falta (por ejemplo, un campo), se corrige en el fixture, no con un parche en el visor.

---

## 7. Tarea 2 — Constructor, escritura y verificación

### Qué es la telemetría

**Telemetría** es el registro automático de lo que ocurre en un sistema mientras funciona, para analizarlo después (como la caja negra de un avión). Aquí es lo que sale de la simulación: los snapshots de cada agente, los mensajes y, al final, las métricas. Vive en `src/harvest_sim/telemetria.py` y su salida es `runs/<escenario>/trace.json`.

**Con quién funciona:**

```
simulacion.py (Carlos), en cada tick:
    registros = [cosechadora.registro(t), carro.registro(t)]   # diccionarios SIN checksum (Emilio y Oswaldo)
    builder.agregar_tick(t, registros)                         # TU código: agrega checksum y guarda

al terminar:
    trace = builder.construir(buzon.registro(), metricas)      # mensajes (Emilio) + métricas (tuyas)
    escribir_trace(trace, "runs/<escenario>/trace.json")       # TU código

después, leen el archivo: el visor (Giovanni), tus gráficas, los tests (Ilan)
```

Los agentes **no conocen** la telemetría: solo exponen `registro()`. La telemetría no toma decisiones: solo **anota hechos**. Las interpretaciones (métricas) se calculan después, desde el archivo.

**Qué debe considerar tu código:**
- **Esquema y versión:** `schema_version: "1.0"` en todo archivo.
- **Integridad:** un checksum por registro, para detectar datos dañados o editados.
- **Determinismo:** sin fechas, horas ni nada que cambie entre corridas; claves ordenadas; formato siempre igual.
- **Tipos serializables:** JSON no tiene tuplas; las celdas van como listas `[x, y]`.
- **Orden estable:** los agentes aparecen siempre en el mismo orden dentro de cada tick.
- **Qué no entra:** combustible ni nada aleatorio (fuera del alcance de esta entrega).

**Cómo se hace, en pequeño** (la idea, no el código final):

```python
class TraceBuilder:
    def __init__(self, config: dict):
        self._config = config          # lo que Carlos le pase (por ejemplo, dataclasses.asdict(config))
        self._ticks = []               # aquí se acumula todo

    def agregar_tick(self, tick, registros):
        # a cada registro le pones su checksum (ya tienes con_checksum) y guardas el tick
        ...

    def construir(self, mensajes, metricas=None):
        # devuelves el diccionario del §6.1: schema_version, escenario, seed, config, ticks, mensajes, metricas
        ...
```

Los tests de esta tarea comprueban que cada registro lleva checksum, que `verificar_checksums` detecta un valor alterado a mano, y que escribir dos veces el mismo trace produce archivos idénticos.

### Las funciones

Son cuatro funciones pequeñas más el constructor. Trabajas sobre las firmas que ya están en `telemetria.py`.

| Función | Qué hace | Detalle importante |
|---|---|---|
| `TraceBuilder(config)` | Guarda la configuración y va acumulando ticks | Convierte el `Config` a diccionario |
| `agregar_tick(tick, registros)` | Recibe los registros **sin checksum** y los guarda con checksum | Usa `con_checksum`. Respeta el orden de los agentes |
| `construir(mensajes, metricas)` | Devuelve el diccionario completo del §6.1 | Pon `schema_version`, `escenario`, `seed`, `config`, `ticks`, `mensajes`, `metricas` |
| `escribir_trace(trace, ruta)` | Escribe el archivo | **Reproducible byte a byte** (ver abajo) |
| `cargar_trace(ruta)` | Lee el archivo | `json.load` |
| `verificar_checksums(trace)` | Recalcula cada checksum y compara | Devuelve `True` solo si **todos** coinciden |

**Reproducibilidad byte a byte** significa que correr dos veces el mismo escenario produce archivos idénticos. Para lograrlo:

- `json.dump(..., sort_keys=True, indent=2, ensure_ascii=False)` y siempre con el mismo formato.
- Termina el archivo con un salto de línea fijo.
- **Nada** que cambie entre corridas: ni fechas ni horas, ni identificadores aleatorios, ni rutas absolutas dentro del archivo.
- Crea la carpeta de salida si no existe (`Path.mkdir(parents=True, exist_ok=True)`).

**Tests que debes escribir** (en `tests/test_telemetria.py`, quita el `skip` de los que ya existen):

- Un registro con checksum bien puesto pasa `verificar_checksums`; si cambias un valor a mano, falla.
- Escribir dos veces el mismo trace produce archivos con el mismo contenido.
- `TraceBuilder` agrega checksum a todos los registros.

**Cuando termines:** avisa a Carlos, quien usa `TraceBuilder` en `simulacion.py`. Si cambias algo de la forma de la API respecto al §3.1 del plan, avísale **antes** de subir.

---

## 8. Tarea 3 — Las métricas

`calcular_metricas(trace)` recibe el trace **ya leído** y devuelve un diccionario. Todo se calcula **desde el log**, no desde la simulación. Así cualquiera puede verificar los números.

| Métrica | En palabras | Cómo sacarla del log |
|---|---|---|
| `tiempo_ocioso_cosechadora` | Cuántos ticks esperó la cosechadora llena a que llegara el carro | Contar snapshots de `cosechadora_1` con `estado == "LLENA_ESPERANDO"`. **Es la métrica principal** |
| `tiempo_transfiriendo` | Ticks pasados transfiriendo | Contar `estado == "TRANSFIRIENDO"` |
| `tick_fin_cosecha` | Cuándo terminó de entregar la última carga | `tick_envio` del último mensaje `TRANSFERENCIA_TERMINADA` |
| `tiempo_completacion` | Cuándo terminó todo (todos en su base) | El último `tick` del log |
| `distancia_cosechadora`, `distancia_carro` | Cuántas celdas se movió cada agente | Contar ticks en que la `pose` (x, y) cambió respecto al tick anterior |
| `distancia_total` | Suma de las dos | — |
| `colisiones` | Ticks con dos agentes en la misma celda o intercambiando posiciones | Comparar las poses de ambos agentes en cada tick. Debe salir 0 |
| `ticks_bloqueados` | Ticks que cada agente esperó por una celda ocupada | Contar `intencion.accion == "ESPERAR_BLOQUEO"`, por agente |
| `num_ciclos` | Cuántas veces se llenó la cosechadora | Contar mensajes `LLENA` |
| `espera_por_ciclo` | Cuánto esperó en cada ciclo | Agrupar los snapshots consecutivos de `LLENA_ESPERANDO` y contar el largo de cada tramo |
| `utilizacion_carro` | Qué fracción del tiempo trabajó el carro | Ticks con el carro en cualquier estado que no sea `EN_BASE`, entre el total de ticks |
| `grano_total_entregado` | Cuánto grano llegó a la bodega | Suma de `cantidad` de los mensajes `TRANSFERENCIA_TERMINADA` |

### Ejemplo trabajado a mano

Supón que la cosechadora tiene estos estados en ticks 10 a 20:

```
tick:    10   11   12   13   14   15   16   17   18   19   20
estado:  COS  COS  LLE  LLE  LLE  LLE  TRA  TRA  COS  COS  COS
```

(`LLE` = `LLENA_ESPERANDO`, `TRA` = `TRANSFIRIENDO`, `COS` = `COSECHANDO`.)

- `tiempo_ocioso_cosechadora` en este tramo = 4 (ticks 12, 13, 14, 15).
- `tiempo_transfiriendo` = 2.
- `espera_por_ciclo` de este ciclo = 4.

Ese cálculo, con números que tú sabes de antemano, es **tu test**: construyes un trace mínimo de ~10 ticks, calculas a mano lo que debería salir y escribes `assert metricas["tiempo_ocioso_cosechadora"] == 4`.

### Consejos

- Escribe una función pequeña por métrica. Son más fáciles de probar.
- Para la ociosa, un recorrido simple por los ticks y un contador basta. No necesitas pandas.
- Si una definición te queda ambigua (por ejemplo, cómo cuentas los ticks de espera si la cosechadora llena nunca recibe carro), **elige una, escríbela en `docs/decisiones.md`** y sigue.
- **No inventes datos que el log no trae.** Si necesitas algo que no está (por ejemplo, saber si un agente esperó por bloqueo), pídele a quien genera el registro que lo incluya. Por eso existe el vocabulario `intencion.accion`.

---

## 9. Tarea 4 — Gráficas y tabla (`viz/plots.py`)

Todas con `matplotlib`, leyendo **solo el JSON** (no importes la simulación). Al inicio del archivo pon `import matplotlib; matplotlib.use("Agg")` para que funcione sin ventana, también en CI.

| # | Gráfica | Qué muestra | Herramienta |
|---|---|---|---|
| 1 | Carga de la cosechadora vs. tiempo | Un diente de sierra: sube al cosechar, cae a 0 al transferir | `plt.plot` o `plt.step` |
| 2 | Línea de tiempo de estados (Gantt) | Una franja de color por estado, para ambos agentes | `ax.broken_barh` |
| 3 | Tiempo ocioso por ciclo | Barras con `espera_por_ciclo` | `plt.bar` |
| 4 | Comparación entre escenarios | Tiempo ocioso, `tick_fin_cosecha`, completación y distancia total, de A, B y C | Barras agrupadas |

Para la **2** (la más informativa): agrupa los snapshots consecutivos con el mismo estado en tramos `(inicio, duración)` y dibújalos con `broken_barh`, con un color fijo por estado y una leyenda.

Además, la tabla resumen: un CSV y una versión en Markdown con una fila por escenario y una columna por métrica. Será lo que el equipo pegue en el reporte.

Reglas de presentación: título, ejes con nombre y unidades ("ticks", "unidades de grano"), leyenda legible, colores fijos por estado (el mismo color significa el mismo estado en todas las gráficas) y archivos guardados con `savefig` en `runs/<escenario>/plots/`.

**Cómo saber que está bien:** pruébalas con el fixture. Si la gráfica 1 y la 2 cuentan la misma historia (cuando la carga llega al máximo, aparece `LLENA_ESPERANDO`), van bien.

---

## 10. Tarea 5 — Corridas reales y análisis (domingo)

Cuando Carlos tenga `ejecutar` funcionando:

1. Corre los tres escenarios y revisa que cada `trace.json` pase `verificar_checksums`.
2. **Revisa que las métricas tengan sentido:**
   - `colisiones == 0`.
   - `grano_total_entregado == ancho × (alto−1) × grano_por_celda`.
   - `tiempo_ocioso` es mayor o igual a 0 y menor que `tiempo_completacion`.
   - `tick_fin_cosecha <= tiempo_completacion`.
3. Si algo no cuadra, **no ajustes los números**: encuentra el motivo con el dueño del módulo (Carlos, Oswaldo o Emilio), con tu fixture y tus tests como evidencia.
4. Genera las gráficas y la tabla.
5. Escribe 5–8 líneas de lectura de resultados. Por ejemplo: qué escenario tuvo más espera y por qué, y cuál es el número que tendrá que mejorar el despacho anticipado. Ese texto lo reutilizarán para el reporte y la presentación.

---

## 11. Cómo saber que vas bien

| Señal de que vas bien | Señal de alerta |
|---|---|
| El fixture abre en el visor de Giovanni | Giovanni te pide "un campo más" cada hora (el esquema no estaba cerrado) |
| `verificar_checksums` da `True` | El checksum falla "a veces" (algo no es determinista) |
| Tus tests de métricas pasan con valores calculados a mano | Los tests usan números que sacaste del propio código |
| Dos corridas dan el mismo archivo | Los archivos difieren en el orden de las claves o en una fecha |
| Las gráficas 1 y 2 cuentan la misma historia | Una gráfica muestra algo que no puedes explicar |

---

## 12. Preguntas frecuentes

**¿Tengo que entender toda la simulación para hacer mi parte?**
No. Solo el §6 de la especificación (el formato del log) y las tablas de estados del §5 para saber qué significa cada estado. Tu trabajo empieza cuando el log ya existe.

**¿Por qué el fixture es inventado y no sale de la simulación real?**
Porque la simulación aún no existe cuando necesitas empezar. El fixture te da datos con los que trabajar y con los que Giovanni dibuja. Cuando exista la simulación real, la comparas con el fixture: deben tener la misma forma.

**¿Y si Carlos o los demás generan el registro distinto a lo que yo espero?**
Se resuelve contra el §3.2 del plan (forma del registro) y el §6.1 de la especificación. Si algo falta, se pide al dueño del módulo o se corrige el contrato y se anota en `docs/decisiones.md`. Tus tests de `verificar_checksums` y de forma del registro detectan el problema temprano.

**¿Puedo usar pandas o numpy?**
Evítalo: la regla del proyecto es no agregar dependencias. Con `json`, `collections` y `matplotlib` alcanza. Si realmente lo necesitas, avisa antes de tocar `requirements.txt`.

**¿Qué hago si el calculo de una métrica es ambiguo?**
Elige la definición más simple, escríbela en `docs/decisiones.md` (qué decidiste, qué alternativa considerabas y por qué), y úsala igual en el código, los tests y el reporte.

**¿A quién le pido ayuda?**
Para el formato del log y el vocabulario de `intencion.accion`: el equipo en la reunión del viernes y `docs/decisiones.md`. Para algo del código de agentes: su dueño (Emilio para cosechadora y mensajes, Oswaldo para el carro). Para algo del visor: Giovanni. Tu respaldo es Giovanni, y tú eres el suyo.
