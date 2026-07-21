"""Motor de cálculo de liquidación de prestaciones sociales según la LOTTT.

Referencias legales (Ley Orgánica del Trabajo, los Trabajadores y las
Trabajadoras - LOTTT, 2012):

* Art. 122  - Definición de salario normal e integral.
* Art. 131  - Utilidades (mínimo 30, máximo 120 días).
* Art. 142  - Garantía y prestaciones sociales (literales a, b, c, d).
* Art. 143  - Intereses sobre prestaciones sociales.
* Art. 92   - Indemnización por terminación injustificada.
* Art. 190  - Vacaciones (15 días + 1 por año, hasta 30).
* Art. 192  - Bono vacacional (15 días + 1 por año, hasta 30).
"""

from __future__ import annotations

from decimal import Decimal
from typing import List

from dateutil.relativedelta import relativedelta

from .models import (
    Antiguedad,
    DatosTrabajador,
    HistorialSalarial,
    LineaConcepto,
    ParametrosCalculo,
    ResultadoLiquidacion,
)
from .money import D, money, rate

# Tope máximo de días adicionales acumulables (Art. 142 lit. b).
TOPE_DIAS_ADICIONALES = 30
# Tope de días de vacaciones/bono vacacional (Art. 190 / 192).
TOPE_DIAS_VACACIONES = 30
DIAS_MES = D("30")
MESES_ANIO = D("12")
DIAS_ANIO_ALICUOTA = D("360")


def _validar_fechas(ingreso, egreso) -> None:
    if ingreso is None or egreso is None:
        raise ValueError("Debe indicar fecha de ingreso y fecha de egreso.")
    if egreso < ingreso:
        raise ValueError(
            "La fecha de egreso no puede ser anterior a la fecha de ingreso."
        )


def calcular_antiguedad(fecha_ingreso, fecha_egreso) -> Antiguedad:
    """Calcula la antigüedad exacta en años, meses y días."""
    _validar_fechas(fecha_ingreso, fecha_egreso)
    rd = relativedelta(fecha_egreso, fecha_ingreso)
    total_dias = (fecha_egreso - fecha_ingreso).days

    # Trimestres completos de servicio (cada 3 meses cumplidos).
    meses_totales = rd.years * 12 + rd.months
    trimestres = meses_totales // 3

    # Fracción del último año (meses + días) superior a 6 meses.
    fraccion_mayor_6 = rd.months > 6 or (rd.months == 6 and rd.days > 0)

    return Antiguedad(
        anios=rd.years,
        meses=rd.months,
        dias=rd.days,
        total_dias=total_dias,
        trimestres_completos=trimestres,
        fraccion_mayor_6_meses=fraccion_mayor_6,
    )


def _dias_por_antiguedad(anios_cumplidos: int, base: int, tope: int) -> int:
    """Días de vacaciones/bono para un año de servicio (Art. 190/192).

    ``anios_cumplidos`` es el número de año que se está causando (1, 2, 3...).
    Primer año = base; +1 por cada año subsiguiente, con tope.
    """
    if anios_cumplidos < 1:
        return base
    return min(base + (anios_cumplidos - 1), tope)


def _dias_adicionales_prestaciones(anios: int) -> int:
    """Días adicionales Art. 142 lit. b: 2 días por año a partir del 2º, tope 30."""
    if anios < 2:
        return 0
    return min(2 * (anios - 1), TOPE_DIAS_ADICIONALES)


def _vacaciones_fraccionadas_dias(
    ant: Antiguedad, base_dias: int, tope: int
) -> Decimal:
    """Días de vacaciones/bono fraccionados por los meses del último año."""
    anio_en_curso = ant.anios + 1
    derecho = _dias_por_antiguedad(anio_en_curso, base_dias, tope)
    return rate(D(derecho) / MESES_ANIO * D(ant.meses))


def calcular_liquidacion(
    trabajador: DatosTrabajador,
    historial: HistorialSalarial,
    parametros: ParametrosCalculo,
) -> ResultadoLiquidacion:
    """Calcula la liquidación completa y devuelve un ``ResultadoLiquidacion``."""

    ant = calcular_antiguedad(trabajador.fecha_ingreso, trabajador.fecha_egreso)
    memoria: List[str] = []

    # --- Salarios (Art. 122) ---
    salario_mensual = historial.salario_mensual_normal()
    salario_diario_normal = rate(salario_mensual / DIAS_MES)
    memoria.append(
        f"Salario mensual normal: Bs. {salario_mensual}. "
        f"Salario diario normal = {salario_mensual} / 30 = Bs. {salario_diario_normal}."
    )

    dias_util = D(parametros.dias_utilidades_anuales)
    dias_bono_base = int(parametros.dias_bono_vacacional_base)
    dias_vac_base = int(parametros.dias_vacaciones_base)

    # Alícuota de utilidades = (salario diario * días utilidades / año) por día.
    alicuota_utilidades = rate(
        salario_diario_normal * dias_util / DIAS_ANIO_ALICUOTA
    )
    # Días de bono vacacional que corresponden al último año de servicio.
    dias_bono_actual = _dias_por_antiguedad(
        ant.anios + 1, dias_bono_base, TOPE_DIAS_VACACIONES
    )
    alicuota_bono = rate(
        salario_diario_normal * D(dias_bono_actual) / DIAS_ANIO_ALICUOTA
    )
    salario_integral_diario = rate(
        salario_diario_normal + alicuota_utilidades + alicuota_bono
    )
    memoria.append(
        f"Alícuota utilidades = {salario_diario_normal} x {dias_util} / 360 "
        f"= Bs. {alicuota_utilidades}."
    )
    memoria.append(
        f"Alícuota bono vacacional = {salario_diario_normal} x {dias_bono_actual} / 360 "
        f"= Bs. {alicuota_bono}."
    )
    memoria.append(
        f"Salario integral diario = {salario_diario_normal} + {alicuota_utilidades} "
        f"+ {alicuota_bono} = Bs. {salario_integral_diario}."
    )

    asignaciones: List[LineaConcepto] = []

    # --- Prestaciones sociales (Art. 142) ---
    dias_garantia = D(15) * D(ant.trimestres_completos)
    dias_adicionales = D(_dias_adicionales_prestaciones(ant.anios))
    monto_garantia = money(
        (dias_garantia + dias_adicionales) * salario_integral_diario
    )
    memoria.append(
        f"Garantía (Art. 142 a/b): {ant.trimestres_completos} trimestres x 15 = "
        f"{dias_garantia} días + {dias_adicionales} días adicionales (Art. 142 c) "
        f"= {dias_garantia + dias_adicionales} días x {salario_integral_diario} "
        f"= Bs. {monto_garantia}."
    )

    dias_retroactivo = D(30) * D(ant.anios_para_retroactivo)
    monto_retroactivo = money(dias_retroactivo * salario_integral_diario)
    memoria.append(
        f"Retroactivo (Art. 142 d): {ant.anios_para_retroactivo} año(s) x 30 = "
        f"{dias_retroactivo} días x {salario_integral_diario} = Bs. {monto_retroactivo}."
    )

    if monto_retroactivo >= monto_garantia:
        prestaciones = monto_retroactivo
        metodo = "Retroactivo (Art. 142 lit. d)"
        dias_prestaciones = dias_retroactivo
    else:
        prestaciones = monto_garantia
        metodo = "Garantía acumulada (Art. 142 lit. a/b/c)"
        dias_prestaciones = dias_garantia + dias_adicionales
    memoria.append(
        f"Se adjudica el monto MAYOR (Art. 142 lit. d): {metodo} = Bs. {prestaciones}."
    )

    asignaciones.append(
        LineaConcepto(
            concepto="Prestaciones sociales (monto mayor)",
            dias=dias_prestaciones,
            base=salario_integral_diario,
            monto=prestaciones,
            formula=metodo,
            articulo="Art. 142 LOTTT",
        )
    )

    # --- Intereses sobre prestaciones (Art. 143) ---
    intereses = D("0")
    if parametros.calcular_intereses and parametros.tasa_interes_anual:
        tasa = D(parametros.tasa_interes_anual) / D(100)
        anios_frac = D(ant.total_dias) / D("365")
        intereses = money(prestaciones * tasa * anios_frac)
        memoria.append(
            f"Intereses (Art. 143): {prestaciones} x {parametros.tasa_interes_anual}% "
            f"x {anios_frac:.4f} año(s) = Bs. {intereses}."
        )
        asignaciones.append(
            LineaConcepto(
                concepto="Intereses sobre prestaciones sociales",
                base=None,
                monto=intereses,
                formula=f"Saldo x tasa anual {parametros.tasa_interes_anual}% x tiempo",
                articulo="Art. 143 LOTTT",
            )
        )

    # --- Indemnización por despido injustificado (Art. 92) ---
    indemnizacion = D("0")
    if trabajador.motivo_retiro.genera_indemnizacion:
        indemnizacion = prestaciones
        memoria.append(
            f"Indemnización (Art. 92): igual al monto de prestaciones = Bs. {indemnizacion}."
        )
        asignaciones.append(
            LineaConcepto(
                concepto="Indemnización por despido injustificado",
                monto=indemnizacion,
                formula="Igual al monto de prestaciones sociales (Art. 92)",
                articulo="Art. 92 LOTTT",
            )
        )

    # --- Vacaciones (Art. 190) ---
    dias_vac_pend = D(parametros.dias_vacaciones_pendientes)
    if dias_vac_pend > 0:
        monto = money(dias_vac_pend * salario_diario_normal)
        asignaciones.append(
            LineaConcepto(
                concepto="Vacaciones vencidas (no disfrutadas)",
                dias=dias_vac_pend,
                base=salario_diario_normal,
                monto=monto,
                formula=f"{dias_vac_pend} días x {salario_diario_normal}",
                articulo="Art. 190 LOTTT",
            )
        )
        memoria.append(
            f"Vacaciones vencidas: {dias_vac_pend} días x {salario_diario_normal} "
            f"= Bs. {monto}."
        )

    dias_vac_frac = _vacaciones_fraccionadas_dias(ant, dias_vac_base, TOPE_DIAS_VACACIONES)
    if dias_vac_frac > 0:
        monto = money(dias_vac_frac * salario_diario_normal)
        asignaciones.append(
            LineaConcepto(
                concepto="Vacaciones fraccionadas",
                dias=dias_vac_frac,
                base=salario_diario_normal,
                monto=monto,
                formula=f"{dias_vac_frac} días x {salario_diario_normal} "
                f"({ant.meses} mes(es) del último año)",
                articulo="Art. 190 / 196 LOTTT",
            )
        )
        memoria.append(
            f"Vacaciones fraccionadas: {dias_vac_frac} días x {salario_diario_normal} "
            f"= Bs. {monto}."
        )

    # --- Bono vacacional (Art. 192) ---
    dias_bono_pend = D(parametros.dias_bono_vacacional_pendientes)
    if dias_bono_pend > 0:
        monto = money(dias_bono_pend * salario_diario_normal)
        asignaciones.append(
            LineaConcepto(
                concepto="Bono vacacional vencido",
                dias=dias_bono_pend,
                base=salario_diario_normal,
                monto=monto,
                formula=f"{dias_bono_pend} días x {salario_diario_normal}",
                articulo="Art. 192 LOTTT",
            )
        )

    dias_bono_frac = _vacaciones_fraccionadas_dias(ant, dias_bono_base, TOPE_DIAS_VACACIONES)
    if dias_bono_frac > 0:
        monto = money(dias_bono_frac * salario_diario_normal)
        asignaciones.append(
            LineaConcepto(
                concepto="Bono vacacional fraccionado",
                dias=dias_bono_frac,
                base=salario_diario_normal,
                monto=monto,
                formula=f"{dias_bono_frac} días x {salario_diario_normal} "
                f"({ant.meses} mes(es) del último año)",
                articulo="Art. 192 LOTTT",
            )
        )

    # --- Utilidades fraccionadas (Art. 131) ---
    # Prorrateo por meses completos del ejercicio fiscal (año de egreso).
    meses_ejercicio = trabajador.fecha_egreso.month
    if (
        trabajador.fecha_ingreso.year == trabajador.fecha_egreso.year
    ):
        # Ingresó el mismo año: contar desde el mes de ingreso.
        meses_ejercicio = (
            trabajador.fecha_egreso.month - trabajador.fecha_ingreso.month + 1
        )
    dias_util_frac = rate(dias_util / MESES_ANIO * D(meses_ejercicio))
    if dias_util_frac > 0:
        monto = money(dias_util_frac * salario_diario_normal)
        asignaciones.append(
            LineaConcepto(
                concepto="Utilidades fraccionadas",
                dias=dias_util_frac,
                base=salario_diario_normal,
                monto=monto,
                formula=f"{dias_util} días/año / 12 x {meses_ejercicio} mes(es) "
                f"= {dias_util_frac} días x {salario_diario_normal}",
                articulo="Art. 131 LOTTT",
            )
        )
        memoria.append(
            f"Utilidades fraccionadas: {dias_util}/12 x {meses_ejercicio} meses "
            f"= {dias_util_frac} días x {salario_diario_normal} = Bs. {monto}."
        )

    # --- Deducciones ---
    deducciones: List[LineaConcepto] = []
    for concepto, valor, art in (
        ("Anticipo de prestaciones sociales", parametros.anticipo_prestaciones, "Art. 144 LOTTT"),
        ("Préstamos / adelantos", parametros.prestamos, ""),
        ("Otras deducciones / retenciones", parametros.otras_deducciones, ""),
    ):
        v = money(valor)
        if v > 0:
            deducciones.append(
                LineaConcepto(concepto=concepto, monto=v, articulo=art)
            )

    total_asignaciones = money(sum((a.monto for a in asignaciones), D(0)))
    total_deducciones = money(sum((d.monto for d in deducciones), D(0)))
    neto = money(total_asignaciones - total_deducciones)
    memoria.append(
        f"TOTAL asignaciones = Bs. {total_asignaciones}; "
        f"TOTAL deducciones = Bs. {total_deducciones}; "
        f"NETO A PAGAR = Bs. {neto}."
    )

    return ResultadoLiquidacion(
        trabajador=trabajador,
        parametros=parametros,
        antiguedad=ant,
        salario_mensual_normal=salario_mensual,
        salario_diario_normal=salario_diario_normal,
        alicuota_utilidades=alicuota_utilidades,
        alicuota_bono_vacacional=alicuota_bono,
        salario_integral_diario=salario_integral_diario,
        dias_garantia=dias_garantia,
        dias_adicionales=dias_adicionales,
        monto_garantia=monto_garantia,
        dias_retroactivo=dias_retroactivo,
        monto_retroactivo=monto_retroactivo,
        prestaciones_sociales=prestaciones,
        metodo_prestaciones=metodo,
        intereses_prestaciones=intereses,
        indemnizacion=indemnizacion,
        asignaciones=asignaciones,
        deducciones=deducciones,
        total_asignaciones=total_asignaciones,
        total_deducciones=total_deducciones,
        neto_pagar=neto,
        memoria=memoria,
    )
