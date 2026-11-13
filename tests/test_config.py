"""Configuración de escenarios.  [Bloque A]"""

import json
from pathlib import Path

import pytest

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
CAMPOS = {
    "nombre", "seed", "ancho", "alto", "num_carros", "num_cosechadoras",
    "grano_por_celda", "capacidad_cosechadora", "capacidad_carro",
    "tasa_transferencia", "tasa_descarga", "max_ticks",
}


@pytest.mark.parametrize("nombre", ["escenario_a", "escenario_b", "escenario_c"])
def test_escenarios_tienen_todos_los_campos(nombre):
    """Humo: los JSON de escenario existen y traen exactamente los campos del §3."""
    datos = json.loads((CONFIG_DIR / f"{nombre}.json").read_text(encoding="utf-8"))
    assert set(datos) == CAMPOS
    assert datos["nombre"] == nombre


@pytest.mark.skip(reason="pendiente — Bloque A")
def test_config_invalida():
    """Las validaciones del §3 fallan con mensaje claro: capacidad_carro < capacidad_cosechadora,
    capacidad no múltiplo de grano_por_celda, ancho < 1+n+m, alto < 2, num_* distinto de 1,
    tasas o cantidades no positivas."""
