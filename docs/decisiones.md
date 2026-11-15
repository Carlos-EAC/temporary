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
  3. Cada tick lleva una **lista cronológica de eventos tipados** (`AGENTE`, `CELDA_COSECHADA`, `DEPOSITO`, `MENSAJE_ENVIADO`, `MENSAJE_ENTREGADO`) con orden fijo por categoría.
  4. Los mensajes van **dentro de los ticks** como eventos (no en una lista aparte) y además se imprimen por consola con `logging` (§6.3 de la especificación).
  5. `intencion.celdas` = próximas celdas de la ruta, **recalculadas en cada tick** (más espacio, pero el visor no deriva la ruta restante).
  6. **Checksum por tick** (sobre `{tick, cambios}` en JSON canónico).
  7. El log guarda **hechos con valores nuevos explícitos** y todo lo derivado ya calculado (orientación, ruta, totales). Colores, sprites y animación son decisión de la herramienta de visualización.
  8. Versión **2.0**: es incompatible con el esquema v1.0 de la propuesta (un registro por agente en cada tick); los campos de v1.0 (`pose`, `estado`, `carga`, `intencion`, `objetivo`) se conservan dentro de `AGENTE.set`.
  9. El archivo se escribe con orden de inserción fijo (no `sort_keys`); el orden canónico se usa solo en el checksum.
- **Alternativas consideradas:** foto completa de agentes y mapa en cada tick (v1.0); agentes completos por tick y solo el mapa por cambios (primera versión del 2026-11-14); `ticks` como diccionario con claves de texto; diccionarios por entidad dentro de cada tick; lista de mensajes aparte; `intencion.celdas` como ruta completa fijada una sola vez; checksum por registro de agente.
- **Por qué se descartaron:** la foto por tick crece como ticks × celdas; el híbrido deja al visor deduciendo el estado del mapa; con `ticks` como diccionario las claves (texto) se ordenan mal al escribir con claves ordenadas (`"10"` antes que `"2"`) y Unity (`JsonUtility`) no lee diccionarios con claves dinámicas; los diccionarios por entidad no admiten dos cambios del mismo agente ni dos mensajes en un tick, y pierden el orden; una lista de mensajes aparte duplica la fuente de verdad; la ruta completa fijada una vez obliga al visor a derivar la ruta restante a partir de la pose (lógica en el visor); el checksum por agente repite huellas en cada registro.
- **Afecta a:** Carlos (`Mundo.descripcion`, `drenar_eventos`), Emilio (`Buzon.drenar_eventos`; `registro()` de la cosechadora), Oswaldo (`registro()` del carro), Joel (`TraceBuilder`, `reconstruir`, métricas), Giovanni (visor y CLI), Ilan (tests).
