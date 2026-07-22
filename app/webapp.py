"""Aplicación Flask del Sistema de Nómina Integral (multiempresa)."""

from __future__ import annotations

import io
import os

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from . import db
from .calc.engine import calcular_liquidacion
from .exporters import generar_excel, generar_pdf
from .forms import ErrorFormulario, form_a_dict, parsear_formulario

SESSION_KEY = "ultimo_formulario"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "sistema-nomina-integral-dev")
    db.init_db()

    def _slug(nombre: str) -> str:
        return "".join(c if c.isalnum() else "_" for c in nombre).strip("_") or "liquidacion"

    @app.route("/")
    def index():
        datos = session.get(SESSION_KEY, {})
        return render_template(
            "index.html", datos=datos, fichas=db.listar_fichas(),
            empresas=db.listar_empresas(),
        )

    # ------------------------------ Empresas ------------------------------
    @app.route("/empresas")
    def empresas():
        return render_template("empresas.html", empresas=db.listar_empresas())

    @app.route("/empresas/guardar", methods=["POST"])
    def guardar_empresa():
        nombre = (request.form.get("nombre") or "").strip()
        if not nombre:
            flash("El nombre de la empresa es obligatorio.", "error")
            return redirect(url_for("empresas"))
        rif = (request.form.get("rif") or "").strip()
        direccion = (request.form.get("direccion") or "").strip()
        empresa_id = request.form.get("empresa_id")
        if empresa_id:
            db.actualizar_empresa(int(empresa_id), nombre, rif, direccion)
            flash("Empresa actualizada.", "ok")
        else:
            db.crear_empresa(nombre, rif, direccion)
            flash("Empresa creada.", "ok")
        return redirect(url_for("empresas"))

    @app.route("/empresas/<int:empresa_id>/eliminar", methods=["POST"])
    def borrar_empresa(empresa_id: int):
        db.eliminar_empresa(empresa_id)
        flash("Empresa eliminada.", "ok")
        return redirect(url_for("empresas"))

    @app.route("/calcular", methods=["POST"])
    def calcular():
        try:
            trabajador, historial, parametros = parsear_formulario(request.form)
            resultado = calcular_liquidacion(trabajador, historial, parametros)
        except (ErrorFormulario, ValueError) as exc:
            flash(str(exc), "error")
            session[SESSION_KEY] = form_a_dict(request.form)
            return redirect(url_for("index"))

        session[SESSION_KEY] = form_a_dict(request.form)
        empresa_id = request.form.get("empresa_id")
        empresa_id = int(empresa_id) if empresa_id else None

        if request.form.get("guardar_ficha"):
            db.guardar_ficha(
                trabajador.nombre, trabajador.cedula, trabajador.cargo,
                session[SESSION_KEY], empresa_id=empresa_id,
            )
            flash("Ficha guardada correctamente.", "ok")

        return render_template("resultado.html", r=resultado)

    def _resultado_desde_sesion():
        datos = session.get(SESSION_KEY)
        if not datos:
            return None
        trabajador, historial, parametros = parsear_formulario(datos)
        return calcular_liquidacion(trabajador, historial, parametros)

    @app.route("/export/pdf")
    def export_pdf():
        resultado = _resultado_desde_sesion()
        if resultado is None:
            flash("Primero realice un cálculo para exportar.", "error")
            return redirect(url_for("index"))
        data = generar_pdf(resultado)
        return send_file(
            io.BytesIO(data), mimetype="application/pdf", as_attachment=True,
            download_name=f"liquidacion_{_slug(resultado.trabajador.nombre)}.pdf",
        )

    @app.route("/export/excel")
    def export_excel():
        resultado = _resultado_desde_sesion()
        if resultado is None:
            flash("Primero realice un cálculo para exportar.", "error")
            return redirect(url_for("index"))
        data = generar_excel(resultado)
        return send_file(
            io.BytesIO(data),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"liquidacion_{_slug(resultado.trabajador.nombre)}.xlsx",
        )

    @app.route("/ficha/<int:ficha_id>")
    def cargar_ficha(ficha_id: int):
        datos = db.obtener_ficha(ficha_id)
        if datos is None:
            flash("Ficha no encontrada.", "error")
            return redirect(url_for("index"))
        session[SESSION_KEY] = datos
        flash("Ficha cargada en el formulario.", "ok")
        return redirect(url_for("index"))

    @app.route("/ficha/<int:ficha_id>/eliminar", methods=["POST"])
    def borrar_ficha(ficha_id: int):
        db.eliminar_ficha(ficha_id)
        flash("Ficha eliminada.", "ok")
        return redirect(url_for("index"))

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}

    return app
