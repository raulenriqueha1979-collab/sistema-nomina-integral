"""Modelos de datos de entrada y salida del motor de cálculo."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Optional


class MotivoRetiro(str, Enum):
    """Motivos de terminación de la relación laboral."""

    RENUNCIA = "renuncia"
    DESPIDO_JUSTIFICADO = "despido_justificado"
    DESPIDO_INJUSTIFICADO = "despido_injustificado"
    FIN_CONTRATO = "fin_contrato"

    @property
    def etiqueta(self) -> str:
        return {
            MotivoRetiro.RENUNCIA: "Renuncia voluntaria",
            MotivoRetiro.DESPIDO_JUSTIFICADO: "Despido justificado",
            MotivoRetiro.DESPIDO_INJUSTIFICADO: "Despido injustificado",
            MotivoRetiro.FIN_CONTRATO: "Fin de contrato / obra determinada",
        }[self]

    @property
    def genera_indemnizacion(self) -> bool:
        """El Art. 92 LOTTT aplica en despido injustificado o retiro justificado."""
        return self == MotivoRetiro.DESPIDO_INJUSTIFICADO


@dataclass
class DatosTrabajador:
    """Ficha identificatoria del trabajador."""

    nombre: str
    cedula: str
    cargo: str = ""
    departamento: str = ""
    fecha_ingreso: date = field(default_factory=date.today)
    fecha_egreso: date = field(default_factory=date.today)
    motivo_retiro: MotivoRetiro = MotivoRetiro.RENUNCIA


@dataclass
class HistorialSalarial:
    """Historial salarial del trabajador.

    Se admiten dos modalidades:

    * Salario fijo: se informa ``salario_mensual`` (Bs/mes).
    * Salario variable: se informa ``salarios_mensuales`` (lista de los
      últimos meses); el motor promedia para obtener el salario normal.
    """

    salario_mensual: Optional[Decimal] = None
    salarios_mensuales: List[Decimal] = field(default_factory=list)

    def salario_mensual_normal(self) -> Decimal:
        from .money import D, money

        if self.salarios_mensuales:
            total = sum((D(s) for s in self.salarios_mensuales), D(0))
            return money(total / D(len(self.salarios_mensuales)))
        if self.salario_mensual is None:
            raise ValueError(
                "Debe indicar salario_mensual o salarios_mensuales."
            )
        return money(self.salario_mensual)


@dataclass
class ParametrosCalculo:
    """Parámetros configurables del cálculo."""

    dias_utilidades_anuales: Decimal = Decimal("30")
    dias_bono_vacacional_base: Decimal = Decimal("15")
    dias_vacaciones_base: Decimal = Decimal("15")
    dias_vacaciones_pendientes: Decimal = Decimal("0")
    dias_bono_vacacional_pendientes: Decimal = Decimal("0")
    # Intereses sobre prestaciones (Art. 143). Tasa anual promedio BCV (%).
    calcular_intereses: bool = False
    tasa_interes_anual: Decimal = Decimal("0")
    # Deducciones
    anticipo_prestaciones: Decimal = Decimal("0")
    prestamos: Decimal = Decimal("0")
    otras_deducciones: Decimal = Decimal("0")
    # Datos de la empresa (para reportes)
    empresa_nombre: str = ""
    empresa_rif: str = ""


@dataclass
class LineaConcepto:
    """Una línea del desglose de la liquidación."""

    concepto: str
    dias: Optional[Decimal] = None
    base: Optional[Decimal] = None  # salario diario aplicado
    monto: Decimal = Decimal("0")
    formula: str = ""
    articulo: str = ""


@dataclass
class Antiguedad:
    anios: int
    meses: int
    dias: int
    total_dias: int
    trimestres_completos: int
    fraccion_mayor_6_meses: bool

    @property
    def anios_para_retroactivo(self) -> int:
        """Años a razón de 30 días (Art. 142): años completos + 1 si fracción > 6 meses."""
        return self.anios + (1 if self.fraccion_mayor_6_meses else 0)

    def descripcion(self) -> str:
        return f"{self.anios} año(s), {self.meses} mes(es) y {self.dias} día(s)"


@dataclass
class ResultadoLiquidacion:
    """Resultado completo de la liquidación."""

    trabajador: DatosTrabajador
    parametros: ParametrosCalculo
    antiguedad: Antiguedad

    salario_mensual_normal: Decimal
    salario_diario_normal: Decimal
    alicuota_utilidades: Decimal
    alicuota_bono_vacacional: Decimal
    salario_integral_diario: Decimal

    # Prestaciones
    dias_garantia: Decimal
    dias_adicionales: Decimal
    monto_garantia: Decimal
    dias_retroactivo: Decimal
    monto_retroactivo: Decimal
    prestaciones_sociales: Decimal
    metodo_prestaciones: str
    intereses_prestaciones: Decimal

    # Indemnización
    indemnizacion: Decimal

    asignaciones: List[LineaConcepto]
    deducciones: List[LineaConcepto]

    total_asignaciones: Decimal
    total_deducciones: Decimal
    neto_pagar: Decimal

    memoria: List[str] = field(default_factory=list)
