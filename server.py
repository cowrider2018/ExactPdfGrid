"""
ExactPdfGrid Web Server
=======================
Flask HTTP server that exposes the pipeline as a REST endpoint.

Usage
-----
    python server.py

Then open http://localhost:5000 in your browser.

POST /convert
    Form field: pdf  (multipart/form-data, file)
    Query params (all optional):
        dpi            (int,   default 200)
        min_line       (int,   default 8)
        ink_threshold  (int,   default 240)
        cluster_gap    (int,   default 8)
    Response: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
"""

from __future__ import annotations
import io
import tempfile
from pathlib import Path

from flask import Flask, request, send_file, jsonify, render_template_string
import fitz

from pdf_to_image import pdf_to_images
from table_detection import detect_line_segments, build_cell_grid, draw_debug
from ocr_processing import extract_cells_text
from xlsx_output import resolve_grid, write_xlsx_workbook

app = Flask(__name__, static_folder="web", static_url_path="")


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    if "pdf" not in request.files:
        return jsonify(error="No pdf file uploaded"), 400

    pdf_file = request.files["pdf"]
    if not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify(error="File must be a PDF"), 400

    dpi           = int(request.form.get("dpi",           200))
    min_line      = int(request.form.get("min_line",       8))
    ink_threshold = int(request.form.get("ink_threshold", 240))
    cluster_gap   = int(request.form.get("cluster_gap",    8))

    # Write uploaded PDF to a temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = Path(tmp.name)
        pdf_file.save(tmp)

    try:
        fitz_doc = fitz.open(str(pdf_path))
        images   = pdf_to_images(str(pdf_path), dpi=dpi)

        sheet_data = []
        for page_index, img in enumerate(images):
            fitz_page = fitz_doc[page_index]

            accepted, rejected = detect_line_segments(
                img,
                min_line_length=min_line,
                ink_threshold=ink_threshold,
            )

            cells, ys, xs = build_cell_grid(accepted, cluster_gap=cluster_gap)

            if not cells:
                continue

            cells = extract_cells_text(fitz_page, cells, dpi=dpi)
            sorted_cells = resolve_grid(cells)
            sheet_data.append((f"Page{page_index + 1}", sorted_cells, ys, xs))

        fitz_doc.close()

        if not sheet_data:
            return jsonify(error="No table cells detected in this PDF"), 422

        # Write workbook to in-memory buffer
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_xlsx:
            xlsx_path = Path(tmp_xlsx.name)

        write_xlsx_workbook(sheet_data, out_path=str(xlsx_path), dpi=dpi)

        xlsx_bytes = xlsx_path.read_bytes()
        xlsx_path.unlink(missing_ok=True)

        stem = Path(pdf_file.filename).stem
        return send_file(
            io.BytesIO(xlsx_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"{stem}.xlsx",
        )

    except Exception as exc:
        return jsonify(error=str(exc)), 500

    finally:
        pdf_path.unlink(missing_ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
