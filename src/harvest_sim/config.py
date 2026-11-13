"""Carga y validación de la configuración de un escenario.  [Bloque A]

Especificación: §3. Todos los parámetros viven en config/*.json; nada de números
mágicos en el resto del código.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    nombre: str
    seed: int
    ancho: int
    alto: int
    num_carros: int
    num_cosechadoras: int
    grano_por_celda: int
    capacidad_cosechadora: int
    capacidad_carro: int
    tasa_transferencia: int  # unidades de grano por tick
    tasa_descarga: int       # unidades de grano por tick
    max_ticks: int


def cargar_config(ruta: str | Path) -> Config:
    """Lee un JSON de escenario, lo valida y devuelve un Config.

    TODO (Bloque A): implementar las validaciones del §3 de la especificación
    (fallar con error claro):
      - capacidad_carro >= capacidad_cosechadora
      - capacidad_cosechadora múltiplo de grano_por_celda
      - ancho >= 1 + num_carros + num_cosechadoras
      - alto >= 2
      - num_carros y num_cosechadoras >= 1; por ahora solo se acepta 1
        ("aún no soportado" en otro caso)
      - tasas y cantidades: enteros positivos
    """
    raise NotImplementedError("Bloque A: cargar_config")
