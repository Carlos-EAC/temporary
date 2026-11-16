# Registro de decisiones de diseño

Anota aquí cada decisión que no esté cubierta por [la especificación](especificacion_primera_entrega.md), o cada cambio al contrato de interfaces (§10 de la especificación).

Formato por entrada:

```
## AAAA-MM-DD — Título corto
- **Quién:** nombre (bloque)
- **Decisión:** qué se decidió
- **Alternativa considerada:** qué otra opción había
- **Por qué se descartó:** razón
- **Afecta a:** bloques o archivos
```

---

<!-- Agrega las entradas debajo, la más reciente al final -->

## 2026-11-15 — Formato del trace v2.0: log de cambios por tick (reemplaza la entrada provisional del 2026-11-14)
- **Estado:** DECIDIDO.
- **Quién:** Joel (Datos)
- **Decisión:**
  1. `trace.json` v2.0: primer nivel estático (`schema_version`, `meta`, `config`, `mundo`, `agentes`), más `ticks` y `metricas`.
  2. `ticks` es un **arreglo** ordenado por tick, solo con los ticks que tienen cambios (el 0 siempre aparece); `meta.total_ticks` da el último tick.
  3. Cada tick lleva una **lista cronológica de eventos tipados** (`AGENTE`, `CELDA_COSECHADA`, `DEPOSITO`, `BLOQUEO`, `MENSAJE_ENVIADO`, `MENSAJE_ENTREGADO`) con orden fijo por categoría.
  4. Los mensajes van **dentro de los ticks** como eventos (no en una lista aparte) y además se imprimen por consola con `logging` (§6.3 de la especificación).
  5. ~~`intencion.celdas` por tick~~ **REEMPLAZADA** por la entrada siguiente: el log no guarda rutas ni intenciones.
  6. **Checksum por tick** (sobre `{tick, cambios}` en JSON canónico).
  7. El log guarda **hechos con valores nuevos explícitos** y todo lo derivado ya calculado (orientación, totales). Colores, sprites y animación son decisión de la herramienta de visualización.
  8. Versión **2.0**: es incompatible con el esquema v1.0 de la propuesta (un registro por agente en cada tick); los campos `pose`, `estado` y `carga` de v1.0 se conservan dentro de `AGENTE.set`; `intencion` y `objetivo` salen (ver la entrada siguiente).
  9. El archivo se escribe con orden de inserción fijo (no `sort_keys`); el orden canónico se usa solo en el checksum.
- **Alternativas consideradas:** foto completa de agentes y mapa en cada tick (v1.0); agentes completos por tick y solo el mapa por cambios (primera versión del 2026-11-14); `ticks` como diccionario con claves de texto; diccionarios por entidad dentro de cada tick; lista de mensajes aparte; `intencion.celdas` como ruta completa fijada una sola vez; checksum por registro de agente.
- **Por qué se descartaron:** la foto por tick crece como ticks × celdas; el híbrido deja al visor deduciendo el estado del mapa; con `ticks` como diccionario las claves (texto) se ordenan mal al escribir con claves ordenadas (`"10"` antes que `"2"`) y Unity (`JsonUtility`) no lee diccionarios con claves dinámicas; los diccionarios por entidad no admiten dos cambios del mismo agente ni dos mensajes en un tick, y pierden el orden; una lista de mensajes aparte duplica la fuente de verdad; la ruta completa fijada una vez obliga al visor a derivar la ruta restante a partir de la pose (lógica en el visor); el checksum por agente repite huellas en cada registro.
- **Afecta a:** Carlos (`Mundo.descripcion`, `drenar_eventos`), Emilio (`Buzon.drenar_eventos`; `registro()` de la cosechadora), Oswaldo (`registro()` del carro), Joel (`TraceBuilder`, `reconstruir`, métricas), Giovanni (visor y CLI), Ilan (tests).

## 2026-11-15 — El log guarda solo cambios explícitos: se quitan `intencion` y `objetivo` y se agrega `BLOQUEO` (corrige la decisión 5 de la entrada anterior)
- **Estado:** DECIDIDO.
- **Quién:** Joel (Datos)
- **Decisión:**
  1. `AGENTE.set` solo lleva `pose`, `estado` y `carga`.
  2. Se quitan `intencion` (acción y celdas) y `objetivo`: el `estado` ya indica a dónde va el agente (`YENDO_A_BODEGA`, `REGRESANDO_A_BASE`…).
  3. Un bloqueo (el agente esperó por una celda ocupada) es un hecho y se registra como evento `BLOQUEO` (`mundo.registrar_bloqueo(agent_id)`); `ticks_bloqueados` cuenta esos eventos.
  4. Criterio general: al log entra solo lo que es un hecho explícito de lo que cambió; nunca algo que el visor tenga que interpretar según el algoritmo del agente.
- **Alternativa considerada:** guardar `intencion.celdas` (próximas celdas en cada tick, o la ruta completa una sola vez) y guardar `intencion.accion` y `objetivo`.
- **Por qué se descartó:** rutas e intenciones dependen del algoritmo (BFS hoy, otro mañana); si estuvieran en el log, el visor tendría que interpretarlas y habría que cambiarlo cada vez que cambie el agente, y la lógica quedaría repartida entre Python y el visor (la propuesta dice que el visor solo reproduce y no decide). Además, repetir en cada tick lo que falta por recorrer es ineficiente: el progreso se expresa con `CELDA_COSECHADA`, como máximo n × m eventos porque una celda no se cosecha dos veces. Una función en el visor sería más compacta, pero repartiría la lógica.
- **Afecta a:** Carlos (`Mundo.registrar_bloqueo`), Emilio y Oswaldo (`registro()` sin `intencion` ni `objetivo`; llamar a `registrar_bloqueo`), Joel (`TraceBuilder`, métricas), Giovanni (visor), Ilan (tests).

## 2026-11-15 — Métricas calculadas desde el log: una por cada variable en juego
- **Estado:** DECIDIDO (revisable cuando cambien las funciones de costo o se agregue el combustible).
- **Quién:** Joel (Datos)
- **Decisión:** todas las métricas se calculan solo desde el `trace.json` (reconstruyendo el estado de cada tick) y hay una por cada variable en juego, para ver el efecto de modificar las funciones de costo sin perder información. Se cuentan los ticks 0..`total_ticks` (ambos incluidos). Definiciones:
  - Tiempo: `tiempo_completacion` = `total_ticks`; `tick_fin_cosecha` = tick del último `TRANSFERENCIA_TERMINADA` enviado (`null` si no hay); `tiempo_ocioso_cosechadora` = ticks en `LLENA_ESPERANDO`; `tiempo_transfiriendo`; `porcentaje_ocioso` = ticks ociosos entre los ticks totales (%); `ticks_por_estado` = ticks de cada agente en cada estado; `espera_por_ciclo` = largo de cada racha consecutiva de `LLENA_ESPERANDO`.
  - Movimiento: `distancia_*` = ticks en que cambió la celda (x, y) del agente (girar sin cambiar de celda no cuenta); `colisiones` = ticks (no pares) con dos agentes en la misma celda o intercambiando posiciones; `ticks_bloqueados` = eventos `BLOQUEO` por agente.
  - Distancia cosechadora–carro: distancia Manhattan por tick; se resume con `_promedio`, `_minima` y `_maxima`.
  - Coordinación: `num_ciclos` = mensajes `LLENA` enviados; `mensajes_enviados` por tipo; `utilizacion_carro` = ticks con el carro fuera de `EN_BASE` entre el total (4 decimales).
  - Grano: `grano_cosechado_total`, `grano_total_entregado` (suma de los `DEPOSITO`), `grano_esperado_total` = `ancho × (alto − 1) × grano_por_celda` y `porcentaje_entregado` (entregado entre esperado, %).
  - Series por tick (`series_temporales`, para las gráficas, no se guardan en el trace): ocioso acumulado, distancia cosechadora–carro, cargas de ambos, grano cosechado acumulado, grano en la bodega y bloqueos acumulados.
  - Pendiente: combustible (todavía no está en el trace).
- **Alternativa considerada:** promedio del ocioso por ciclo o entre corridas; distancia solo por ciclo, en el momento del aviso `LLENA`; calcular las métricas dentro de la simulación; contar pares de colisión; contar solo los ticks que aparecen en el archivo.
- **Por qué se descartó:** se prefiere ver el ocioso acumulado en el tiempo (la curva muestra el total hasta cada tick) y la distancia por tick; las métricas deben poder recalcularse desde el log para ser verificables; los ticks omitidos también cuentan.
- **Afecta a:** Joel (`calcular_metricas`, `series_temporales`); el resto del equipo solo las lee del `trace.json` (clave `metricas`).

## 2026-11-16 — Sentido de cada métrica al comparar contra la línea base
- **Estado:** DECIDIDO (revisable cuando cambien las funciones de costo).
- **Quién:** Joel (Datos)
- **Decisión:** "mejor" es lo que aprovecha mejor los recursos disponibles, sobre todo el tiempo. Al comparar una corrida nueva contra la línea base del mismo escenario (mismo mapa, mismos agentes y misma seed), cada métrica se marca como mejora, empeora, igual, distinta (si es informativa) o sin datos:
  - **Menor es mejor:** tiempos (completación, fin de la cosecha, ocioso, % ocioso, transferencia), distancias (de cada agente, total, cosechadora–carro promedio y máxima), colisiones, bloqueos y ticks en estados de espera (`LLENA_ESPERANDO`, `ESPERANDO_TRANSFERENCIA`, `EN_BASE`).
  - **Mayor es mejor:** utilización del carro, grano cosechado, grano entregado y % entregado.
  - **Informativas** (no dependen de la coordinación): número de ciclos, mensajes por tipo, distancia cosechadora–carro mínima, grano esperado y ticks en los demás estados.
  - Las métricas que son conteos por clave (ticks por estado, bloqueos, mensajes) valen 0 si la clave no aparece en una corrida. Las listas (`espera_por_ciclo`) no se comparan.
  - Una diferencia de config fuera del mapa, los agentes y la seed (por ejemplo, un parámetro de la estrategia nueva) se permite y se informa.
- **Alternativa considerada:** un solo puntaje combinado (por ejemplo, la función de costo J); comparar solo el tiempo ocioso.
- **Por qué se descartó:** un puntaje combinado oculta qué cambió y obliga a fijar pesos antes de tiempo; comparar solo el ocioso pierde información. Ver todas las métricas permite revisar el efecto de cambiar las funciones de costo.
- **Nota:** la utilización del carro puede bajar aunque la corrida mejore, si el mismo trabajo se hace en menos tiempo (el carro pasa proporcionalmente más tiempo en su base). Hay que leerla junto con el tiempo de completación.
- **Afecta a:** Joel (`comparar_metricas`, `comparar_corridas`, `viz/comparar.py`).
