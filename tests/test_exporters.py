"""Verifica que los exportadores generen archivos válidos."""

from datetime import date
from decimal import Decimal

from app.calc.engine import calcular_liquidacion
from app.calc.models import (
    DatosTrabajador,
    HistorialSalarial,
    MotivoRetiro,
    ParametrosCalculo,
)
from app.exporters import generar_excel, generar_pdf


def _resultado():
    trab = DatosTrabajador(
        nombre="Test Export", cedula="V-999",
        fecha_ingreso=date(2019, 5, 1), fecha_egreso=date(2024, 3, 31),
        motivo_retiro=MotivoRetiro.DESPIDO_INJUSTIFICADO,
    )
    hist = HistorialSalarial(salario_mensual=Decimal("4500"))
    par = ParametrosCalculo(
        dias_utilidades_anuales=Decimal("90"),
        empresa_nombre="Mi Empresa, C.A.", empresa_rif="J-12345678-9",
        calcular_intereses=True, tasa_interes_anual=Decimal("28"),
    )
    return calcular_liquidacion(trab, hist, par)


def test_pdf_es_valido():
    data = generar_pdf(_resultado())
    assert data[:4] == b"%PDF"
    assert len(data) > 1500


def test_excel_es_valido():
    data = generar_excel(_resultado())
    # Los .xlsx son ZIP (PK\x03\x04)
    assert data[:2] == b"PK"
    assert len(data) > 2000
