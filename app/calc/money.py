"""Utilidades de manejo monetario con precisión de centavos (Decimal)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Union

Number = Union[int, float, str, Decimal]

CENT = Decimal("0.01")
FOUR = Decimal("0.0001")


def D(value: Number) -> Decimal:
    """Convierte cualquier valor numérico a Decimal de forma segura.

    Los ``float`` se pasan por ``str`` para evitar el ruido binario
    (p. ej. 0.1 -> 0.1 y no 0.1000000000000000055).
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def money(value: Number) -> Decimal:
    """Redondea un valor a 2 decimales (centavos) con redondeo comercial."""
    return D(value).quantize(CENT, rounding=ROUND_HALF_UP)


def rate(value: Number) -> Decimal:
    """Redondea a 4 decimales (útil para alícuotas y salarios diarios)."""
    return D(value).quantize(FOUR, rounding=ROUND_HALF_UP)
