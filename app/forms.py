"""Parseo y validación de los datos del formulario web."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Tuple

from .calc.models import (
    DatosTrabajador,
    HistorialSalarial,
    MotivoRetiro,
    ParametrosCalculo,
)


class ErrorFormulario(ValueError):
    """Error de validación de datos de entrada."""


def _dec(valor, campo: str, default: str = "0") -> Decimal:
    valor = (valor or "").strip()
    if valor == "":
        valor = default
    try:
        d = Decimal(valor.replace(",", "."))
    except (InvalidOperation, AttributeError):
        raise ErrorFormulario(f"El campo '{campo}' debe ser un número válido.")
    if d < 0:
        raise ErrorFormulario(f"El campo '{campo}' no puede ser negativo.")
    return d


def _fecha(valor, campo: str) -> date:
    valor = (valor or "").strip()
    if not valor:
        raise ErrorFormulario(f"Debe indicar la fecha de '{campo}'.")
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        raise ErrorFormulario(f"La fecha de '{campo}' no es válida (formato AAAA-MM-DD).")


def parsear_formulario(form: Dict) -> Tuple[DatosTrabajador, HistorialSalarial, ParametrosCalculo]:
    """Convierte los datos crudos del formulario en modelos del motor de cálculo."""
    nombre = (form.get("nombre") or "").strip()
    cedula = (form.get("cedula") or "").strip()
    if not nombre:
        raise ErrorFormulario("El nombre del trabajador es obligatorio.")
    if not cedula:
        raise ErrorFormulario("La cédula del trabajador es obligatoria.")

    ingreso = _fecha(form.get("fecha_ingreso"), "ingreso")
    egreso = _fecha(form.get("fecha_egreso"), "egreso")
    if egreso < ingreso:
        raise ErrorFormulario("La fecha de egreso no puede ser anterior a la de ingreso.")

    try:
        motivo = MotivoRetiro(form.get("motivo_retiro") or "renuncia")
    except ValueError:
        raise ErrorFormulario("Motivo de retiro no válido.")

    trabajador = DatosTrabajador(
        nombre=nombre,
        cedula=cedula,
        cargo=(form.get("cargo") or "").strip(),
        departamento=(form.get("departamento") or "").strip(),
        fecha_ingreso=ingreso,
        fecha_egreso=egreso,
        motivo_retiro=motivo,
    )

    tipo_salario = form.get("tipo_salario", "fijo")
    if tipo_salario == "variable":
        crudos = form.get("salarios_mensuales", "")
        valores = [v.strip() for v in crudos.replace(";", ",").split(",") if v.strip()]
        if not valores:
            raise ErrorFormulario("Debe indicar al menos un salario mensual para el modo variable.")
        salarios = [_dec(v, "salario mensual") for v in valores]
        historial = HistorialSalarial(salarios_mensuales=salarios)
    else:
        historial = HistorialSalarial(
            salario_mensual=_dec(form.get("salario_mensual"), "salario mensual")
        )

    parametros = ParametrosCalculo(
        dias_utilidades_anuales=_dec(form.get("dias_utilidades"), "días de utilidades", "30"),
        dias_bono_vacacional_base=_dec(form.get("dias_bono_base"), "días base bono vacacional", "15"),
        dias_vacaciones_base=_dec(form.get("dias_vac_base"), "días base vacaciones", "15"),
        dias_vacaciones_pendientes=_dec(form.get("dias_vac_pendientes"), "vacaciones pendientes", "0"),
        dias_bono_vacacional_pendientes=_dec(form.get("dias_bono_pendientes"), "bono vacacional pendiente", "0"),
        calcular_intereses=form.get("calcular_intereses") in ("on", "true", "1", "yes"),
        tasa_interes_anual=_dec(form.get("tasa_interes"), "tasa de interés", "0"),
        anticipo_prestaciones=_dec(form.get("anticipo_prestaciones"), "anticipo de prestaciones", "0"),
        prestamos=_dec(form.get("prestamos"), "préstamos", "0"),
        otras_deducciones=_dec(form.get("otras_deducciones"), "otras deducciones", "0"),
        empresa_nombre=(form.get("empresa_nombre") or "").strip(),
        empresa_rif=(form.get("empresa_rif") or "").strip(),
    )

    _validar_topes(parametros)
    return trabajador, historial, parametros


def _validar_topes(par: ParametrosCalculo) -> None:
    if not (Decimal("30") <= par.dias_utilidades_anuales <= Decimal("120")):
        raise ErrorFormulario(
            "Los días de utilidades deben estar entre 30 y 120 (Art. 131 LOTTT)."
        )


def form_a_dict(form: Dict) -> Dict:
    """Extrae los campos relevantes del formulario para guardar/reconstruir."""
    campos = [
        "empresa_id",
        "nombre", "cedula", "cargo", "departamento", "fecha_ingreso", "fecha_egreso",
        "motivo_retiro", "tipo_salario", "salario_mensual", "salarios_mensuales",
        "dias_utilidades", "dias_bono_base", "dias_vac_base", "dias_vac_pendientes",
        "dias_bono_pendientes", "calcular_intereses", "tasa_interes",
        "anticipo_prestaciones", "prestamos", "otras_deducciones",
        "empresa_nombre", "empresa_rif",
    ]
    return {c: form.get(c, "") for c in campos}
