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

## 2026-11-15 — Definiciones de las métricas calculadas desde el log
- **Estado:** DECIDIDO.
- **Quién:** Joel (Datos)
- **Decisión:** las métricas del §6.2 se calculan solo desde el `trace.json` (reconstruyendo el estado de cada tick) con estas definiciones: se cuentan los ticks 0..`total_ticks` (ambos incluidos); `tiempo_completacion` = `total_ticks`; `distancia_*` = ticks en que cambió la celda (x, y) del agente (un cambio solo de orientación no cuenta); `colisiones` = ticks (no pares) con dos agentes en la misma celda o intercambiando posiciones; `ticks_bloqueados` = eventos `BLOQUEO`, un valor por agente (`{agent_id: n}`); `num_ciclos` = mensajes `LLENA` enviados; `espera_por_ciclo` = largo de cada racha consecutiva de `LLENA_ESPERANDO`; `tick_fin_cosecha` = tick del último `TRANSFERENCIA_TERMINADA` enviado (`null` si no hay); `utilizacion_carro` = ticks con el carro fuera de `EN_BASE` entre el total de ticks, redondeado a 4 decimales.
- **Alternativa considerada:** calcular las métricas dentro de la simulación; contar pares de colisión en vez de ticks; contar solo los ticks que aparecen en el archivo.
- **Por qué se descartó:** las métricas deben poder recalcularse desde el log para ser verificables; los ticks omitidos también son ticks de espera o de movimiento detenido y deben contarse.
- **Afecta a:** Joel (`calcular_metricas`); el resto del equipo solo las lee del `trace.json` (clave `metricas`).
