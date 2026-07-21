"""Generación del recibo de finiquito de liquidación en PDF (ReportLab)."""

from __future__ import annotations

import io
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..calc.models import ResultadoLiquidacion

AZUL = colors.HexColor("#1f3864")
GRIS = colors.HexColor("#f2f2f2")


def _bs(valor: Decimal) -> str:
    return f"Bs. {valor:,.2f}"


def generar_pdf(resultado: ResultadoLiquidacion) -> bytes:
    """Genera el recibo de finiquito en PDF y devuelve los bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="Recibo de Finiquito de Liquidación",
    )

    styles = getSampleStyleSheet()
    h_empresa = ParagraphStyle(
        "empresa", parent=styles["Title"], fontSize=15, textColor=AZUL,
        spaceAfter=2, alignment=TA_CENTER,
    )
    h_sub = ParagraphStyle(
        "sub", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER,
        textColor=colors.grey,
    )
    h_titulo = ParagraphStyle(
        "titulo", parent=styles["Heading2"], fontSize=12, textColor=AZUL,
        alignment=TA_CENTER, spaceBefore=10, spaceAfter=8,
    )
    clausula = ParagraphStyle(
        "clausula", parent=styles["Normal"], fontSize=8.5, alignment=TA_JUSTIFY,
        leading=12,
    )

    trab = resultado.trabajador
    par = resultado.parametros
    elems = []

    # --- Encabezado empresa ---
    elems.append(Paragraph(par.empresa_nombre or "SISTEMA DE CONTROL FISCAL RR", h_empresa))
    if par.empresa_rif:
        elems.append(Paragraph(f"RIF: {par.empresa_rif}", h_sub))
    elems.append(Paragraph("RECIBO DE FINIQUITO DE LIQUIDACIÓN DE PRESTACIONES SOCIALES", h_titulo))
    elems.append(Spacer(1, 4))

    # --- Datos del trabajador ---
    datos = [
        ["Trabajador:", trab.nombre, "C.I.:", trab.cedula],
        ["Cargo:", trab.cargo or "-", "Departamento:", trab.departamento or "-"],
        ["Fecha ingreso:", str(trab.fecha_ingreso), "Fecha egreso:", str(trab.fecha_egreso)],
        ["Motivo de retiro:", trab.motivo_retiro.etiqueta, "Antigüedad:", resultado.antiguedad.descripcion()],
    ]
    t = Table(datos, colWidths=[3.2 * cm, 5.8 * cm, 3.2 * cm, 4.8 * cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 6))

    # --- Bases salariales ---
    bases = [
        ["Salario mensual", _bs(resultado.salario_mensual_normal),
         "Salario diario normal", _bs(resultado.salario_diario_normal)],
        ["Alícuota utilidades", _bs(resultado.alicuota_utilidades),
         "Alícuota bono vacacional", _bs(resultado.alicuota_bono_vacacional)],
        ["", "", "Salario integral diario", _bs(resultado.salario_integral_diario)],
    ]
    tb = Table(bases, colWidths=[4.2 * cm, 4.4 * cm, 4.4 * cm, 4.0 * cm])
    tb.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BACKGROUND", (0, 0), (-1, -1), GRIS),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    elems.append(tb)
    elems.append(Spacer(1, 10))

    # --- Tabla de conceptos ---
    filas = [["CONCEPTO", "Art.", "Días", "Base (Bs.)", "Monto (Bs.)"]]
    for a in resultado.asignaciones:
        filas.append([
            a.concepto,
            a.articulo.replace(" LOTTT", ""),
            f"{a.dias:g}" if a.dias is not None else "",
            f"{a.base:,.2f}" if a.base is not None else "",
            f"{a.monto:,.2f}",
        ])
    filas.append(["TOTAL ASIGNACIONES", "", "", "", f"{resultado.total_asignaciones:,.2f}"])

    for d in resultado.deducciones:
        filas.append([f"(-) {d.concepto}", d.articulo.replace(" LOTTT", ""), "", "", f"{d.monto:,.2f}"])
    filas.append(["TOTAL DEDUCCIONES", "", "", "", f"{resultado.total_deducciones:,.2f}"])
    filas.append(["NETO A PAGAR", "", "", "", f"{resultado.neto_pagar:,.2f}"])

    tabla = Table(filas, colWidths=[7.2 * cm, 2.2 * cm, 1.6 * cm, 2.9 * cm, 3.1 * cm], repeatRows=1)
    estilo = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    # Resaltar filas de totales
    idx_total_asig = 1 + len(resultado.asignaciones)
    idx_neto = len(filas) - 1
    estilo.append(("FONTNAME", (0, idx_total_asig), (-1, idx_total_asig), "Helvetica-Bold"))
    estilo.append(("BACKGROUND", (0, idx_total_asig), (-1, idx_total_asig), GRIS))
    estilo.append(("FONTNAME", (0, idx_neto), (-1, idx_neto), "Helvetica-Bold"))
    estilo.append(("BACKGROUND", (0, idx_neto), (-1, idx_neto), AZUL))
    estilo.append(("TEXTCOLOR", (0, idx_neto), (-1, idx_neto), colors.white))
    estilo.append(("FONTSIZE", (0, idx_neto), (-1, idx_neto), 10))
    tabla.setStyle(TableStyle(estilo))
    elems.append(tabla)
    elems.append(Spacer(1, 16))

    # --- Cláusula legal de finiquito ---
    texto = (
        f"Yo, <b>{trab.nombre}</b>, titular de la cédula de identidad N° <b>{trab.cedula}</b>, "
        f"declaro que he recibido de <b>{par.empresa_nombre or 'la empresa'}</b> la cantidad de "
        f"<b>{_bs(resultado.neto_pagar)}</b> por concepto de pago total y definitivo de mis "
        "prestaciones sociales y demás conceptos laborales derivados de la relación de trabajo, "
        "calculados conforme a la Ley Orgánica del Trabajo, los Trabajadores y las Trabajadoras "
        "(LOTTT) y su Reglamento. Manifiesto mi total conformidad y declaro que nada más se me "
        "adeuda por los conceptos aquí liquidados, otorgando el más amplio y formal finiquito de ley."
    )
    elems.append(Paragraph(texto, clausula))
    elems.append(Spacer(1, 40))

    # --- Firmas ---
    firmas = [
        ["_______________________________", "_______________________________"],
        ["EL TRABAJADOR", "POR LA EMPRESA"],
        [f"C.I.: {trab.cedula}", "Representación legal"],
    ]
    tf = Table(firmas, colWidths=[8.5 * cm, 8.5 * cm])
    tf.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
    ]))
    elems.append(tf)

    doc.build(elems)
    return buffer.getvalue()
