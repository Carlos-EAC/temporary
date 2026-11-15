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

## 2026-11-14 — El mapa se registra como cambios (no una foto por tick) y se agrega log de consola
- **Estado:** PROVISIONAL. El principio (el mapa como cambios, visor sin lógica, log de consola) está decidido; la estructura exacta del `trace.json` está en revisión (ver `docs/propuesta_formato_trace.md` cuando se suba). No implementar `TraceBuilder.construir` hasta que se cierre.
- **Quién:** Joel (Datos)
- **Decisión:** `trace.json` incluye `mundo` (descripción estática calculada por Python) y `cambios` (lista de `CELDA_COSECHADA` y `DEPOSITO`, solo cuando ocurren). Los registros de agente siguen completos por tick. Los mensajes siguen en el log y además se imprimen por consola con `logging` (§6.3 de la especificación).
- **Alternativa considerada:** foto completa del mapa en cada tick; y deducir celdas cosechadas en el visor a partir de las posiciones.
- **Por qué se descartó:** la foto crece como ticks × celdas; deducir en el visor duplica reglas del juego fuera de Python (la simulación es la fuente de verdad, y Unity solo visualiza).
- **Afecta a:** Carlos (`Mundo.cambios`, `descripcion`, `tick_actual`), Joel (`TraceBuilder.construir`), Emilio (log del `Buzon`), Giovanni (visor y CLI), Ilan (tests nuevos).
