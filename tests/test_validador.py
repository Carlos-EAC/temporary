"""Validador del trace (tarea 6 de Datos).  [Dueño: Joel]

Cada prueba altera una copia del fixture para romper UNA regla, vuelve a calcular los checksums (para
que el único error sea el buscado, salvo en la prueba del checksum) y comprueba que el validador lo
reporta con un mensaje que dice dónde está.
"""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from harvest_sim.telemetria import calcular_checksum, cargar_trace, validar_trace

RAIZ = Path(__file__).resolve().parents[1]
FIXTURE = RAIZ / "tests" / "fixtures" / "trace_ejemplo.json"
H, C = "cosechadora_1", "carro_1"


def cargar_modulo(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def base():
    return cargar_trace(FIXTURE)


def resellar(trace):
    for t in trace["ticks"]:
        t["checksum"] = calcular_checksum({"tick": t["tick"], "cambios": t["cambios"]})
    return trace


def tick(trace, numero):
    return next(t for t in trace["ticks"] if t["tick"] == numero)


def evento(trace, tipo, condicion=lambda e: True):
    """(tick, evento) del primer evento de ese tipo que cumpla la condición."""
    for t in trace["ticks"]:
        for e in t["cambios"]:
            if e["tipo"] == tipo and condicion(e):
                return t, e
    raise AssertionError(f"no hay evento {tipo} que cumpla la condición")


def errores_de(base, alterar, sellar=True):
    trace = copy.deepcopy(base)
    alterar(trace)
    return validar_trace(resellar(trace) if sellar else trace)


def contiene(errores, *fragmentos):
    return any(all(f in e for f in fragmentos) for e in errores)


# --- Trazas válidas ------------------------------------------------------------------------------
def test_el_fixture_es_valido(base):
    assert validar_trace(base) == []


def test_las_variantes_del_generador_son_validas():
    gen = cargar_modulo("generar_trace_ejemplo", RAIZ / "tools" / "generar_trace_ejemplo.py")
    for cambios in ({}, dict(ancho=5, capacidad_cosechadora=4, capacidad_carro=8, tasa_transferencia=2),
                    dict(tasa_transferencia=2, tasa_descarga=3)):
        assert validar_trace(gen.generar(dict(gen.CONFIG, **cambios))) == [], cambios


def test_no_falla_con_entradas_que_no_son_un_trace():
    assert validar_trace([]) == ["el trace no es un objeto JSON"]
    assert validar_trace({}) != []


# --- Estructura ----------------------------------------------------------------------------------
def test_orden_de_las_claves_del_primer_nivel(base):
    def alterar(t):
        meta = t.pop("meta")
        t["meta"] = meta
    assert contiene(errores_de(base, alterar), "orden de las claves del primer nivel")


def test_version_del_esquema(base):
    def alterar(t):
        t["schema_version"] = "1.0"
    assert contiene(errores_de(base, alterar), "schema_version", "'1.0'")


def test_falta_un_dato_del_mundo(base):
    def alterar(t):
        del t["mundo"]["bodega"]
    assert contiene(errores_de(base, alterar), "mundo: falta bodega")


def test_agente_repetido_en_el_catalogo(base):
    def alterar(t):
        t["agentes"].append(copy.deepcopy(t["agentes"][0]))
    assert contiene(errores_de(base, alterar), "id repetido")


# --- Ticks ---------------------------------------------------------------------------------------
def test_checksum_alterado(base):
    def alterar(t):
        tick(t, 4)["cambios"][0]["set"]["carga"] = 0
    assert contiene(errores_de(base, alterar, sellar=False), "tick 4", "checksum")


def test_ticks_desordenados(base):
    def alterar(t):
        t["ticks"][3], t["ticks"][4] = t["ticks"][4], t["ticks"][3]
    assert contiene(errores_de(base, alterar), "estrictamente crecientes")


def test_falta_el_tick_0(base):
    def alterar(t):
        t["ticks"].pop(0)
    errores = errores_de(base, alterar)
    assert contiene(errores, "el primer tick debe ser el 0")


def test_tick_mayor_que_total_ticks(base):
    def alterar(t):
        t["meta"]["total_ticks"] = 30
    assert contiene(errores_de(base, alterar), "mayor que meta.total_ticks")


# --- Eventos -------------------------------------------------------------------------------------
def test_tipo_de_evento_desconocido(base):
    def alterar(t):
        tick(t, 4)["cambios"].append({"tipo": "INVENTADO"})
    assert contiene(errores_de(base, alterar), "tick 4", "tipo desconocido 'INVENTADO'")


def test_faltan_campos_en_un_evento(base):
    def alterar(t):
        _, e = evento(t, "DEPOSITO")
        del e["entregado_total"]
    assert contiene(errores_de(base, alterar), "(DEPOSITO)", "faltan campos ['entregado_total']")


def test_campos_extra_en_un_evento(base):
    def alterar(t):
        _, e = evento(t, "BLOQUEO")
        e["motivo"] = "celda ocupada"
    assert contiene(errores_de(base, alterar), "(BLOQUEO)", "campos no esperados ['motivo']")


def test_tipo_de_dato_incorrecto(base):
    def alterar(t):
        _, e = evento(t, "DEPOSITO")
        e["cantidad"] = "3"
    assert contiene(errores_de(base, alterar), "(DEPOSITO)", "tipo de dato incorrecto en ['cantidad']")


def test_eventos_fuera_de_orden_dentro_del_tick(base):
    def alterar(t):
        t_, _ = evento(t, "MENSAJE_ENTREGADO")
        t_["cambios"].reverse()  # el AGENTE queda antes de la entrega
    assert contiene(errores_de(base, alterar), "fuera de orden")


# --- Agentes -------------------------------------------------------------------------------------
def test_set_con_campos_no_permitidos(base):
    def alterar(t):
        _, e = evento(t, "AGENTE", lambda e: "pose" in e["set"])
        e["set"]["intencion"] = {"accion": "MOVER", "celdas": []}
    assert contiene(errores_de(base, alterar), "campos no permitidos en set ['intencion']")


def test_agente_fuera_del_catalogo(base):
    def alterar(t):
        _, e = evento(t, "BLOQUEO")
        e["agente"] = "tractor_9"
    assert contiene(errores_de(base, alterar), "'tractor_9' no está en el catálogo")


def test_tick_0_incompleto(base):
    def alterar(t):
        del tick(t, 0)["cambios"][1]["set"]["carga"]
    assert contiene(errores_de(base, alterar), "tick 0", "carro_1", "le faltan ['carga']")


def test_orientacion_invalida(base):
    def alterar(t):
        _, e = evento(t, "AGENTE", lambda e: "pose" in e["set"])
        e["set"]["pose"]["orientacion"] = "NE"
    assert contiene(errores_de(base, alterar), "orientacion 'NE'")


def test_pose_fuera_del_mapa(base):
    def alterar(t):
        tick(t, 0)["cambios"][1]["set"]["pose"]["x"] = 99
    assert contiene(errores_de(base, alterar), "tick 0", "fuera del mapa")


def test_carga_mayor_que_la_capacidad(base):
    def alterar(t):
        _, e = evento(t, "AGENTE", lambda e: e["id"] == H and "carga" in e["set"])
        e["set"]["carga"] = 99
    assert contiene(errores_de(base, alterar), "carga 99", "capacidad (3)")


# --- Mundo ---------------------------------------------------------------------------------------
def test_celda_cosechada_dos_veces(base):
    def alterar(t):
        t_, e = evento(t, "CELDA_COSECHADA")
        t_["cambios"].append(copy.deepcopy(e))
    assert contiene(errores_de(base, alterar), "se cosecha dos veces")


def test_celda_fuera_del_campo(base):
    def alterar(t):
        _, e = evento(t, "CELDA_COSECHADA")
        e["celda"] = [1, 0]  # la fila 0 es de servicio, no es campo
    assert contiene(errores_de(base, alterar), "fuera del campo")


def test_entregado_total_inconsistente(base):
    def alterar(t):
        _, e = evento(t, "DEPOSITO")
        e["entregado_total"] = e["cantidad"] + 1
    t_, e = evento(base, "DEPOSITO")
    assert contiene(errores_de(base, alterar), f"tick {t_['tick']}", "(DEPOSITO)",
                    f"entregado_total {e['cantidad'] + 1}, se esperaba {e['cantidad']}")


# --- Mensajes ------------------------------------------------------------------------------------
def test_entrega_sin_envio_previo(base):
    def alterar(t):
        _, e = evento(t, "MENSAJE_ENTREGADO")
        e["id"] = 99
    assert contiene(errores_de(base, alterar), "el mensaje 99 no corresponde a un envío previo")


def test_entrega_en_debe_ser_el_tick_siguiente(base):
    def alterar(t):
        _, e = evento(t, "MENSAJE_ENVIADO")
        e["entrega_en"] += 1
    assert contiene(errores_de(base, alterar), "(MENSAJE_ENVIADO)", "entrega_en")


def test_mensaje_que_nunca_se_entrega(base):
    def alterar(t):
        t_, e = evento(t, "MENSAJE_ENTREGADO")
        t_["cambios"].remove(e)
    assert contiene(errores_de(base, alterar), "nunca se entregó")


def test_ids_de_mensaje_no_crecientes(base):
    def alterar(t):
        enviados = [e for x in t["ticks"] for e in x["cambios"] if e["tipo"] == "MENSAJE_ENVIADO"]
        enviados[1]["id"] = enviados[0]["id"]
    assert contiene(errores_de(base, alterar), "repetido")


# --- Línea de comandos ---------------------------------------------------------------------------
def test_cli_ok_y_errores(tmp_path, capsys, base):
    cli = cargar_modulo("validar_trace", RAIZ / "tools" / "validar_trace.py")
    assert cli.main([str(FIXTURE)]) == 0
    assert capsys.readouterr().out.strip().endswith(": OK")

    roto = copy.deepcopy(base)
    roto["schema_version"] = "1.0"
    ruta_rota = tmp_path / "roto.json"
    ruta_rota.write_text(json.dumps(roto), encoding="utf-8")
    ilegible = tmp_path / "ilegible.json"
    ilegible.write_text("{esto no es json", encoding="utf-8")
    assert cli.main([str(FIXTURE), str(ruta_rota), str(ilegible)]) == 1
    salida = capsys.readouterr().out
    assert "roto.json: 1 error(es)" in salida and "schema_version" in salida
    assert "ilegible.json: no se pudo leer" in salida
