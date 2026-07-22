"""Tests unitarios del motor de cálculo (verificación al centavo)."""

from datetime import date
from decimal import Decimal

import pytest

from app.calc.engine import (
    calcular_antiguedad,
    calcular_liquidacion,
)
from app.calc.models import (
    DatosTrabajador,
    HistorialSalarial,
    MotivoRetiro,
    ParametrosCalculo,
)


def D(x):
    return Decimal(str(x))


# --------------------------------------------------------------------------
# Antigüedad y validación de fechas
# --------------------------------------------------------------------------
def test_antiguedad_exacta():
    ant = calcular_antiguedad(date(2018, 3, 15), date(2023, 10, 20))
    assert (ant.anios, ant.meses, ant.dias) == (5, 7, 5)
    assert ant.trimestres_completos == 22  # (5*12+7)//3
    assert ant.fraccion_mayor_6_meses is True
    assert ant.anios_para_retroactivo == 6


def test_antiguedad_un_anio():
    ant = calcular_antiguedad(date(2023, 1, 1), date(2024, 1, 1))
    assert (ant.anios, ant.meses, ant.dias) == (1, 0, 0)
    assert ant.total_dias == 365
    assert ant.trimestres_completos == 4
    assert ant.fraccion_mayor_6_meses is False
    assert ant.anios_para_retroactivo == 1


def test_fraccion_exacta_6_meses_no_cuenta():
    # 6 meses exactos NO es fracción "superior" a 6 meses.
    ant = calcular_antiguedad(date(2023, 1, 15), date(2023, 7, 15))
    assert ant.meses == 6 and ant.dias == 0
    assert ant.fraccion_mayor_6_meses is False


def test_egreso_anterior_a_ingreso():
    with pytest.raises(ValueError):
        calcular_antiguedad(date(2024, 1, 1), date(2023, 1, 1))


# --------------------------------------------------------------------------
# Caso A: 1 año exacto, renuncia, salario fijo 3000
# --------------------------------------------------------------------------
def _caso_a():
    trab = DatosTrabajador(
        nombre="Ana Prueba",
        cedula="V-12345678",
        fecha_ingreso=date(2023, 1, 1),
        fecha_egreso=date(2024, 1, 1),
        motivo_retiro=MotivoRetiro.RENUNCIA,
    )
    hist = HistorialSalarial(salario_mensual=D(3000))
    par = ParametrosCalculo(dias_utilidades_anuales=D(30))
    return calcular_liquidacion(trab, hist, par)


def test_caso_a_salarios():
    r = _caso_a()
    assert r.salario_diario_normal == D("100.0000")
    assert r.alicuota_utilidades == D("8.3333")
    assert r.alicuota_bono_vacacional == D("4.4444")
    assert r.salario_integral_diario == D("112.7777")


def test_caso_a_prestaciones_gana_garantia():
    r = _caso_a()
    assert r.dias_garantia == D(60)
    assert r.dias_adicionales == D(0)
    assert r.monto_garantia == D("6766.66")
    assert r.monto_retroactivo == D("3383.33")
    assert r.prestaciones_sociales == D("6766.66")
    assert "Garantía" in r.metodo_prestaciones


def test_caso_a_totales():
    r = _caso_a()
    # Prestaciones 6766.66 + utilidades fraccionadas 250.00
    assert r.total_asignaciones == D("7016.66")
    assert r.total_deducciones == D("0.00")
    assert r.neto_pagar == D("7016.66")
    assert r.indemnizacion == D("0")


# --------------------------------------------------------------------------
# Caso B: 5a 7m 5d, despido injustificado, salario fijo 6000, utilidades 60
# --------------------------------------------------------------------------
def _caso_b():
    trab = DatosTrabajador(
        nombre="Beto Prueba",
        cedula="V-87654321",
        fecha_ingreso=date(2018, 3, 15),
        fecha_egreso=date(2023, 10, 20),
        motivo_retiro=MotivoRetiro.DESPIDO_INJUSTIFICADO,
    )
    hist = HistorialSalarial(salario_mensual=D(6000))
    par = ParametrosCalculo(
        dias_utilidades_anuales=D(60),
        dias_vacaciones_pendientes=D(30),
        anticipo_prestaciones=D(5000),
        prestamos=D(1000),
    )
    return calcular_liquidacion(trab, hist, par)


def test_caso_b_salario_integral():
    r = _caso_b()
    assert r.salario_diario_normal == D("200.0000")
    assert r.salario_integral_diario == D("244.4444")


def test_caso_b_prestaciones_e_indemnizacion():
    r = _caso_b()
    assert r.dias_adicionales == D(8)  # 2*(5-1)
    assert r.dias_garantia == D(330)  # 22 trimestres * 15
    assert r.monto_garantia == D("82622.21")
    assert r.monto_retroactivo == D("43999.99")
    assert r.prestaciones_sociales == D("82622.21")
    # Art. 92: indemnización igual a prestaciones
    assert r.indemnizacion == D("82622.21")


def test_caso_b_totales():
    r = _caso_b()
    assert r.total_deducciones == D("6000.00")
    assert r.total_asignaciones == D("185911.10")
    assert r.neto_pagar == D("179911.10")


# --------------------------------------------------------------------------
# Intereses (Art. 143) y salario variable
# --------------------------------------------------------------------------
def test_intereses_opcionales():
    trab = DatosTrabajador(
        nombre="C", cedula="V-1",
        fecha_ingreso=date(2022, 1, 1),
        fecha_egreso=date(2024, 1, 1),
        motivo_retiro=MotivoRetiro.RENUNCIA,
    )
    hist = HistorialSalarial(salario_mensual=D(3000))
    par = ParametrosCalculo(calcular_intereses=True, tasa_interes_anual=D(30))
    r = calcular_liquidacion(trab, hist, par)
    assert r.intereses_prestaciones > 0
    conceptos = [a.concepto for a in r.asignaciones]
    assert any("Intereses" in c for c in conceptos)


def test_salario_variable_promedio():
    hist = HistorialSalarial(salarios_mensuales=[D(3000), D(3600), D(4200)])
    # Promedio = 3600 -> diario 120
    assert hist.salario_mensual_normal() == D("3600.00")


def test_neto_nunca_pierde_centavos():
    """El neto debe ser exactamente asignaciones - deducciones."""
    r = _caso_b()
    assert r.neto_pagar == r.total_asignaciones - r.total_deducciones
