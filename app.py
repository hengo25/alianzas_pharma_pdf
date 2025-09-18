# app.py
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from firebase_utils import obtener_productos, agregar_producto, actualizar_producto, eliminar_producto
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime
import requests
import math

app = Flask(__name__)
app.secret_key = "cualquier_cadena_secreta_local"  # para flash si quieres


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/productos")
def productos():
    q = request.args.get("q", "").strip().lower()
    pagina_actual = int(request.args.get("pagina", 1))
    por_pagina = int(request.args.get("por_pagina", 9))  # por ejemplo 9 (3x3)

    lista = obtener_productos()
    # ordenar alfabéticamente por nombre (insensible a mayúsculas)
    lista.sort(key=lambda p: (p.get("nombre") or "").lower())

    if q:
        lista = [p for p in lista if q in (p.get("nombre") or "").lower()]

    total = len(lista)
    total_paginas = max(1, math.ceil(total / por_pagina))
    if pagina_actual < 1:
        pagina_actual = 1
    if pagina_actual > total_paginas:
        pagina_actual = total_paginas

    start = (pagina_actual - 1) * por_pagina
    end = start + por_pagina
    productos_pagina = lista[start:end]

    return render_template(
        "productos.html",
        productos=productos_pagina,
        todos_productos=lista,
        q=q,
        pagina_actual=pagina_actual,
        total_paginas=total_paginas,
        por_pagina=por_pagina
    )


@app.route("/productos/agregar", methods=["POST"])
def productos_agregar():
    nombre = request.form.get("nombre")
    precio = request.form.get("precio")
    imagen = request.files.get("imagen")
    if not (nombre and precio and imagen):
        flash("Faltan datos para agregar el producto.", "danger")
        return redirect(url_for("productos"))
    agregar_producto(nombre, precio, imagen)
    return redirect(url_for("productos"))


@app.route("/productos/editar/<id>", methods=["POST"])
def productos_editar(id):
    nombre = request.form.get("nombre")
    precio = request.form.get("precio")
    imagen = request.files.get("imagen")
    actualizar_producto(id, nombre, precio, nueva_imagen=imagen)
    return redirect(url_for("productos"))


@app.route("/productos/eliminar/<id>", methods=["POST"])
def productos_eliminar(id):
    eliminar_producto(id)
    return redirect(url_for("productos"))


@app.route("/productos/pdf", methods=["POST"])
def productos_pdf():
    ids = request.form.getlist("productos_seleccionados")
    if not ids:
        flash("No seleccionaste productos para el PDF.", "warning")
        return redirect(url_for("productos"))

    all_products = obtener_productos()
    seleccionados = [p for p in all_products if p.get("id") in ids]

    # --- generar PDF ---
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    story = []

    # Encabezado empresa + fecha (tarjeta superior)
    empresa = "ALIANZAS PHARMA"
    fecha = datetime.now().strftime("%d/%m/%Y")
    story.append(Paragraph(f"<b>{empresa}</b>", styles["Title"]))
    story.append(Paragraph(f"Fecha: {fecha}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Organizamos en filas de 3 tarjetas
    cols = 3
    rows = []
    row = []
    for i, p in enumerate(seleccionados, start=1):
        # descargamos la imagen (si falla, usamos un placeholder)
        img_flowable = None
        try:
            resp = requests.get(p.get("imagen", ""), timeout=10)
            img_buf = BytesIO(resp.content)
            img_flowable = Image(img_buf, width=150, height=120)
        except Exception:
            img_flowable = Paragraph("(imagen no disponible)", styles["Normal"])

        card = [
            img_flowable,
            Spacer(1, 6),
            Paragraph(f"<b>{p.get('nombre','')}</b>", styles["Heading4"]),
            Paragraph(f"${p.get('precio','')}", styles["Normal"])
        ]
        # Convertir cada card a Table para bordes
        t = Table([[card]], colWidths=(160,))
        t.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 8),
        ]))
        row.append(t)

        if i % cols == 0:
            rows.append(row)
            row = []
    if row:
        # completar fila vacías si es necesario
        while len(row) < cols:
            row.append("")  # celda vacía
        rows.append(row)

    # Construir tabla principal con filas
    if rows:
        main_table = Table(rows, colWidths=[(A4[0] - 60) / cols] * cols, hAlign="LEFT")
        main_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(main_table)

    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="catalogo_alinezas_pharma.pdf", mimetype="application/pdf")


if __name__ == "__main__":
    app.run(debug=True)
