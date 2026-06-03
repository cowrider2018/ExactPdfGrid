# ExactPdfGrid

Extract bordered tables from PDFs and export them to Excel (`.xlsx`).

ExactPdfGrid detects table grid lines with OpenCV, reconstructs the cell
layout (including merged cells), and writes a faithful `.xlsx` workbook with
one sheet per page. Text is pulled from the PDF's native vector layer by
default; for scanned PDFs you can swap in a RapidOCR backend.

The package ships **three usable surfaces** for the same pipeline:

- **Library** — call from Python: `import exactpdfgrid; exactpdfgrid("in.pdf")`.
- **API server** — Flask app exposing `POST /convert`, started with `exactpdfgrid-web`.
- **Web UI** — static HTML/JS served by that same server at `GET /`, a drag-and-drop front end to the API.

**Python ≥ 3.9** · Windows / macOS / Linux · default engine is OCR-free.

---

## Install

```bash
pip install exactpdfgrid
```

Optional extras:

```bash
pip install "exactpdfgrid[ocr]"        # RapidOCR + OpenVINO (default, recommended)
pip install "exactpdfgrid[ocr-onnx]"   # RapidOCR + ONNX Runtime (fallback)
pip install "exactpdfgrid[ocr-all]"    # both OCR backends installed
pip install "exactpdfgrid[web]"        # Flask web UI / API server
pip install "exactpdfgrid[all]"        # everything (web + OpenVINO OCR)
```

The `[ocr]` extra installs the unified `rapidocr` package plus the
`openvino` runtime so OCR runs on Intel's OpenVINO by default —
typically 1.5–3× faster than ONNX Runtime on Intel CPU/GPU and
supported on Python 3.9–3.13. Pick `[ocr-onnx]` if OpenVINO is
unavailable on your platform or conflicts with your environment; the
produced `.xlsx` is identical either way.

---

## 1. Library — basic usage

The package is callable. Three positional arguments cover most use cases:
`(pdf_path, engine, out_dir)`. The call returns the `pathlib.Path` of the
generated workbook (or `None` if no tables were detected).

```python
import exactpdfgrid

# Most explicit form
xlsx_path = exactpdfgrid("input.pdf", "pymupdf", "output")
print(xlsx_path)                          # output/input.xlsx

# Use defaults: engine="pymupdf", out_dir="output"
exactpdfgrid("input.pdf")

# Switch to OCR (requires the [ocr] extra)
exactpdfgrid("input.pdf", "rapidocr", "out/")
```

Equivalent forms — pick whichever reads best:

```python
import exactpdfgrid
from exactpdfgrid import PYMUPDF, RAPIDOCR, RAPIDOCR_VINO, RAPIDOCR_ONNX, run

exactpdfgrid("input.pdf", RAPIDOCR, "out/")        # auto: OpenVINO, falls back to ONNX
exactpdfgrid("input.pdf", RAPIDOCR_VINO, "out/")   # force OpenVINO (errors if not installed)
exactpdfgrid("input.pdf", RAPIDOCR_ONNX, "out/")   # force ONNX Runtime
run("input.pdf", RAPIDOCR, "out/")                 # explicit function (no module-callable magic)
```

`exactpdfgrid(...)`, `exactpdfgrid.run(...)`, and `exactpdfgrid.process_pdf(...)`
all share the same underlying pipeline; the first two are shorthands.

---

## 2. Library — advanced usage

When you need to retune the pipeline, use `process_pdf` with three config
dataclasses. Every field has a default that reproduces the out-of-the-box
behavior — set only what you want to change.

```python
from exactpdfgrid import (
    process_pdf,
    DetectionConfig,
    ExtractionConfig,
    OutputConfig,
    normalize_whitespace,
    strip_square_brackets,
    split_at_first_paren,
)

det = DetectionConfig(
    dpi=300,
    min_line_length=10,
    ink_threshold=235,
    dilate_kernel=(3, 3),
    dilate_iterations=1,
    cluster_gap=8,
)

ext = ExtractionConfig(
    engine="rapidocr",
    padding_px=3,
    clean_pipeline=[
        normalize_whitespace,
        strip_square_brackets,     # remove "[note]" annotations
        split_at_first_paren,      # keep only text before the first "("
    ],
)

out = OutputConfig(apply_borders=True, min_col_width=6.0)

xlsx_path = process_pdf(
    "input.pdf",
    detection=det,
    extraction=ext,
    output=out,
    out_dir="output",
)
```

### Config field reference

| Config | Fields |
| :--- | :--- |
| `DetectionConfig` | `dpi`, `min_line_length`, `ink_threshold`, `max_gap`, `aspect_ratio`, `cluster_gap`, `dilate_kernel`, `dilate_iterations`, `morph_open_iterations`, `border_thickness`, `border_density` |
| `ExtractionConfig` | `engine` (`str` or `TextExtractor`), `padding_px`, `clean_pipeline` (`list[Callable[[str], str]]`) |
| `OutputConfig` | `apply_borders`, `apply_size_hints`, `min_col_width`, `min_row_height`, `px_per_char_calibration` |

### Custom cleaners

A cleaner is any `Callable[[str], str]`. The pipeline applies them in order to
each cell's raw extracted text:

```python
from exactpdfgrid import ExtractionConfig, normalize_whitespace

def lower_and_strip(s: str) -> str:
    return s.strip().lower()

ext = ExtractionConfig(clean_pipeline=[normalize_whitespace, lower_and_strip])
```

Built-in cleaners (importable from `exactpdfgrid`):
`normalize_whitespace`, `strip_square_brackets`, `strip_parentheses`,
`split_at_first_paren`, `strip_outer_whitespace`.

### Custom text extractor

Plug in your own OCR / extraction engine by subclassing `TextExtractor`:

```python
from exactpdfgrid import TextExtractor, ExtractionConfig, process_pdf

class MyExtractor(TextExtractor):
    name = "mine"

    def extract(self, *, fitz_page, image, cell, dpi, padding_px) -> str:
        # fitz_page: PyMuPDF page  ·  image: BGR numpy array of the rendered page
        # cell: CellRegion with pixel coords
        return "..."

process_pdf("input.pdf", extraction=ExtractionConfig(engine=MyExtractor()))
```

---

## 3. CLI

The `exactpdfgrid` console script is installed alongside the library and is a
thin wrapper around `process_pdf`:

```bash
exactpdfgrid input.pdf --out output --dpi 300 --engine rapidocr
```

| Flag | Default | Notes |
| :--- | :--- | :--- |
| `--dpi` | `200` | Render resolution. |
| `--out` | `output` | Output directory. |
| `--engine` | `pymupdf` | `pymupdf`, `rapidocr` (auto: OpenVINO → ONNX fallback), `rapidocr-vino` (force OpenVINO), or `rapidocr-onnx` (force ONNX). |
| `--min-line` | `8` | Minimum line length (px). |
| `--ink-threshold` | `240` | Brightness ceiling for "ink". |
| `--cluster-gap` | `8` | Max gap when clustering grid lines (px). |
| `--aspect-ratio` | `40.0` | Aspect-ratio threshold for line blobs. |
| `--border-thickness` | `6` | Half-thickness for border probe. |
| `--border-density` | `0.20` | Ink density threshold. |

Run `exactpdfgrid --help` for the full list.

---

## 4. API server

The `[web]` extra installs a Flask app that exposes the pipeline as a REST
endpoint.

### Install & launch

```bash
pip install "exactpdfgrid[web]"
exactpdfgrid-web                          # binds 0.0.0.0:5000
# or
python -m exactpdfgrid.web.server
```

### Routes

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `GET`  | `/`        | Serves the Web UI (`index.html`). |
| `POST` | `/convert` | Converts a PDF and returns the `.xlsx` payload. |

### `POST /convert` reference

Request body must be `multipart/form-data`.

| Field | Type | Default | Notes |
| :--- | :--- | :--- | :--- |
| `pdf` | file | — | **Required.** The PDF to convert. |
| `dpi` | int | `200` | Render DPI. |
| `min_line` | int | `8` | Minimum line length (px). |
| `ink_threshold` | int | `240` | Brightness ceiling for "ink". |
| `cluster_gap` | int | `8` | Grid-line cluster gap (px). |
| `aspect_ratio` | float | `40.0` | Line blob aspect ratio. |
| `engine` | str | `pymupdf` | `pymupdf`, `rapidocr` (auto), `rapidocr-vino`, or `rapidocr-onnx` (the latter three require an OCR extra on the server: `[ocr]` for OpenVINO, `[ocr-onnx]` for ONNX Runtime). |

Responses:

| Status | Content-Type | Body |
| :--- | :--- | :--- |
| `200` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | `.xlsx` file attachment named `<pdf-stem>.xlsx`. |
| `400` | `application/json` | `{"error": "No pdf file uploaded"}` / `{"error": "File must be a PDF"}` |
| `422` | `application/json` | `{"error": "No table cells detected in this PDF"}` |
| `500` | `application/json` | `{"error": "..."}` for any unhandled server error. |

### Calling the API

**`curl`**:

```bash
curl -X POST http://localhost:5000/convert \
     -F "pdf=@input.pdf" \
     -F "engine=rapidocr" \
     -F "dpi=300" \
     -o output.xlsx
```

**Python `requests`**:

```python
import requests

with open("input.pdf", "rb") as fh:
    response = requests.post(
        "http://localhost:5000/convert",
        files={"pdf": fh},
        data={"engine": "rapidocr", "dpi": 300},
    )

response.raise_for_status()
with open("output.xlsx", "wb") as out:
    out.write(response.content)
```

### Deployment notes

- The development server binds `0.0.0.0:5000` with `debug=False`. For
  production, front it with a real WSGI server (e.g. `gunicorn`):
  ```bash
  gunicorn -w 4 -b 0.0.0.0:5000 exactpdfgrid.web.server:app
  ```
- Each request renders the full PDF in memory and writes a temp `.xlsx`;
  both are cleaned up before the response returns. Plan worker concurrency
  and request timeouts accordingly for large PDFs.
- The endpoint has no built-in authentication. If exposed beyond localhost,
  place it behind a reverse proxy that handles auth and TLS.

---

## 5. Web UI

When the API server is running, `GET /` serves a single-page UI from
`src/exactpdfgrid/web/static/`. It is a thin front end for `POST /convert`,
not a separate service.

Features:

- **PDF drop zone** — drag-and-drop or click-to-select a PDF.
- **Advanced settings panel** (collapsible) — DPI, minimum line length, ink
  threshold, aspect ratio, cluster gap. These map 1-to-1 to the
  `POST /convert` form fields.
- **Convert & download** button — posts to `/convert` and triggers a browser
  download of the returned `.xlsx`.
- **Inline status area** — shows progress and errors returned by the server.

The UI currently exposes the detection-stage knobs; the `engine` field is not
yet surfaced in the form and defaults to `pymupdf`. Use the REST API directly
or the library if you need OCR from a non-browser client.

---

## 6. How it works

1. **Render** — PyMuPDF rasterises each page at the requested DPI.
2. **Detect** — OpenCV morphology + a connectivity check find the horizontal
   and vertical line segments that form the table.
3. **Reconstruct** — pure geometry assembles the segments into a logical
   grid, including merged cells.
4. **Extract** — for each cell, the chosen `TextExtractor` reads the text
   (PyMuPDF clip-extract by default; RapidOCR on the cell crop if selected —
   accelerated by OpenVINO when the `[ocr]` extra is installed).
5. **Clean** — text passes through your `clean_pipeline`.
6. **Write** — `openpyxl` produces an `.xlsx` with proper merges, borders,
   and approximate column widths / row heights derived from the pixel grid.

---

## License

MIT.
