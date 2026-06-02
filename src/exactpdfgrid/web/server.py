"""
ExactPdfGrid Web Server
=======================
Flask HTTP server exposing the pipeline as a REST endpoint.

Install
-------
    pip install 'exactpdfgrid[web]'

Run
---
    exactpdfgrid-web
    # or: python -m exactpdfgrid.web.server

Then open http://localhost:5000 in your browser.

POST /convert
    Form field: pdf  (multipart/form-data, file)
    Form fields (all optional):
        dpi            (int,   default 200)
        min_line       (int,   default 8)
        ink_threshold  (int,   default 240)
        cluster_gap    (int,   default 8)
        aspect_ratio   (float, default 40.0)
        engine         (str,   default "pymupdf"; also accepts
                        "rapidocr" / "rapidocr-vino" / "rapidocr-onnx" when
                        the matching OCR extra is installed on the server)
"""

from __future__ import annotations
import io
import tempfile
from pathlib import Path

try:
    from flask import Flask, jsonify, request, send_file
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "The web server requires the 'web' extra. "
        "Install with: pip install 'exactpdfgrid[web]'"
    ) from e

from ..config import DetectionConfig, ExtractionConfig, OutputConfig
from ..core import process_pdf

_STATIC_DIR = str(Path(__file__).parent / "static")

app = Flask(__name__, static_folder=_STATIC_DIR, static_url_path="")


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

    det = DetectionConfig(
        dpi=int(request.form.get("dpi", 200)),
        min_line_length=int(request.form.get("min_line", 8)),
        ink_threshold=int(request.form.get("ink_threshold", 240)),
        cluster_gap=int(request.form.get("cluster_gap", 8)),
        aspect_ratio=float(request.form.get("aspect_ratio", 40.0)),
    )
    ext = ExtractionConfig(engine=request.form.get("engine", "pymupdf"))
    out_cfg = OutputConfig()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = Path(tmp.name)
        pdf_file.save(tmp)

    work_dir = Path(tempfile.mkdtemp(prefix="exactpdfgrid_"))

    try:
        xlsx_path = process_pdf(
            pdf_path,
            detection=det,
            extraction=ext,
            output=out_cfg,
            out_dir=work_dir,
            write_debug_images=False,
            save_page_pngs=False,
        )
        if xlsx_path is None or not xlsx_path.exists():
            return jsonify(error="No table cells detected in this PDF"), 422

        xlsx_bytes = xlsx_path.read_bytes()
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
        # Best-effort cleanup of the per-request work dir.
        for p in sorted(work_dir.rglob("*"), reverse=True):
            try:
                if p.is_file():
                    p.unlink()
                else:
                    p.rmdir()
            except OSError:
                pass
        try:
            work_dir.rmdir()
        except OSError:
            pass


def main() -> int:
    """Console-script entry point for `exactpdfgrid-web`."""
    app.run(host="0.0.0.0", port=5000, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
