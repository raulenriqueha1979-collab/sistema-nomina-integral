# Sistema de Nómina Integral

Sistema web local **multiempresa** para el **cálculo de liquidación de prestaciones sociales,
vacaciones, bono vacacional y utilidades**, ajustado a la legislación laboral vigente en Venezuela
(**LOTTT** — Ley Orgánica del Trabajo, los Trabajadores y las Trabajadoras — y su Reglamento).

El sistema es transparente en la fórmula utilizada (incluye *memoria de cálculo* paso a paso)
y permite exportar el **recibo de finiquito en PDF** y un **informe detallado en Excel**.

## Características

- **Motor de cálculo con precisión de centavos** (`Decimal`), con tests unitarios.
- Diferenciación entre **salario normal** y **salario integral** (alícuotas de utilidades y
  bono vacacional).
- **Prestaciones sociales (Art. 142)**: garantía trimestral (15 días/trimestre), días
  adicionales (2 por año a partir del 2.º, tope 30) y retroactivo (30 días/año), adjudicando
  siempre el **monto mayor** al trabajador.
- **Intereses sobre prestaciones (Art. 143)**, opcionales, según tasa anual BCV.
- **Indemnización por despido injustificado (Art. 92)**.
- **Vacaciones y bono vacacional (Art. 190 / 192)**: vencidas y fraccionadas.
- **Utilidades (Art. 131)**: mínimo 30 y máximo 120 días, prorrateadas por meses del ejercicio.
- **Deducciones**: anticipos de prestaciones, préstamos y otras retenciones.
- **Validación exacta de fechas** (antigüedad en años, meses y días).
- **Gestión multiempresa**: registra todas las empresas que necesites y asócialas a cada liquidación.
- Guardado opcional de **fichas** de trabajadores (SQLite).
- Exportación a **PDF** (ReportLab) y **Excel** (openpyxl).

## Stack técnico

| Componente | Tecnología |
|------------|------------|
| Backend    | Python 3.10+ / Flask |
| Cálculo de fechas | python-dateutil |
| PDF        | ReportLab |
| Excel      | openpyxl |
| Persistencia | SQLite (opcional) |

## Estructura del proyecto

```
sistema-nomina-integral/
├── app/
│   ├── calc/               # Motor de cálculo (núcleo, sin dependencias web)
│   │   ├── models.py       # Modelos de datos (dataclasses)
│   │   ├── money.py        # Utilidades Decimal / redondeo
│   │   └── engine.py       # Lógica de liquidación (LOTTT)
│   ├── exporters/
│   │   ├── pdf_export.py   # Recibo de finiquito (PDF)
│   │   └── excel_export.py # Resumen + memoria de cálculo (Excel)
│   ├── templates/          # Vistas Jinja2
│   ├── static/             # Hoja de estilos
│   ├── forms.py            # Parseo y validación del formulario
│   ├── db.py               # Persistencia de empresas y fichas (SQLite)
│   └── webapp.py           # Rutas Flask (create_app)
├── tests/                  # Tests unitarios (pytest)
├── run.py                  # Entrada local (dev)
├── wsgi.py                 # Entrada WSGI (producción)
└── requirements.txt
```

## Instalación y ejecución local

Requiere **Python 3.10 o superior**.

```bash
# 1. Clonar y entrar al proyecto
cd sistema-nomina-integral

# 2. Crear y activar un entorno virtual
python3 -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar la aplicación
python run.py
```

Abrir en el navegador: <http://127.0.0.1:5000>

## Ejecutar los tests

```bash
source .venv/bin/activate
pip install pytest
python -m pytest -q
```

Los tests verifican la matemática **al centavo** con casos de prueba reales
(1 año exacto, antigüedad de 5 años 7 meses con despido injustificado, salario variable, etc.).

## Flujo de uso

1. **Empresa**: selecciona una empresa registrada (o créala en la sección *Empresas*) para el
   encabezado del recibo. Puedes registrar tantas empresas como quieras.
2. **Ficha del trabajador** (nombre, C.I., cargo, fechas y motivo de retiro).
3. **Historial salarial**: salario fijo o variable (promedio de meses).
4. **Parámetros**: días de utilidades (30–120), vacaciones pendientes, intereses, etc.
5. **Deducciones**: anticipos, préstamos y retenciones.
6. Pulsar **Calcular liquidación** para ver el desglose transparente y la memoria de cálculo.
7. **Exportar** el recibo en PDF o el informe en Excel.

## Notas legales sobre el cálculo

- El salario integral diario incorpora las alícuotas de **utilidades** y de **bono vacacional**.
- En prestaciones (Art. 142) se calcula tanto la **garantía acumulada** (con días adicionales)
  como el **retroactivo** y se paga el **mayor** de ambos.
- La **indemnización (Art. 92)** se genera únicamente cuando el motivo es *despido injustificado*.
- Cuando se dispone únicamente del salario actual, la garantía y el retroactivo se calculan
  sobre el **último salario integral** (supuesto documentado; usar historial mensual para
  salarios variables).

> **Aviso**: herramienta de apoyo al cálculo. Verifique siempre los resultados con su asesoría
> legal y las tasas oficiales del BCV vigentes.
