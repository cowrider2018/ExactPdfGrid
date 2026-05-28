# ExactPdfGrid

從具邊框的 PDF 表格中辨識儲存格格線，並匯出為 Excel（.xlsx）。提供：

- **Python 套件 API**（`exactpdfgrid.process_pdf(...)`）
- **CLI**（`exactpdfgrid <pdf>`）
- **Web 介面**（`exactpdfgrid-web`，Flask）

需求
- Python ≥ 3.9
- Windows / macOS / Linux

---

## 安裝

### 可編輯模式（推薦給開發者）

```powershell
python -m pip install -e .
```

加上 optional extras：

```powershell
# Web UI（Flask）
python -m pip install -e ".[web]"

# OCR 後端（RapidOCR，可處理掃描型 PDF）
python -m pip install -e ".[ocr]"

# 全部
python -m pip install -e ".[all]"
```

### 一鍵啟動 Web 介面（Windows）

雙擊根目錄的 `start.bat`：
1. 建立 `.venv`（若不存在）
2. `pip install -e ".[web]"`
3. 啟動 Flask 伺服器
4. 自動開啟瀏覽器至 `http://localhost:5000`

---

## CLI 使用

```powershell
exactpdfgrid input.pdf --out output --dpi 300
```

主要旗標：

| 旗標 | 預設 | 說明 |
| :--- | :--- | :--- |
| `--dpi` | 200 | 渲染解析度 |
| `--out` | `output` | 輸出目錄 |
| `--min-line` | 8 | 最小線段長度 (px) |
| `--ink-threshold` | 240 | 視為墨水的亮度上限 |
| `--cluster-gap` | 8 | 格線聚類最大距離 |
| `--aspect-ratio` | 40.0 | 線段長寬比門檻 |
| `--engine` | `pymupdf` | 文字抽取引擎 (`pymupdf` / `rapidocr`) |

---

## Python API

### Shorthand（callable module）

最簡寫法 — `import exactpdfgrid` 後直接呼叫套件：

```python
import exactpdfgrid

# 一行搞定：(pdf_path, engine, out_dir)
exactpdfgrid("input.pdf", "rapidocr", "outputpath")

# 使用預設引擎 (PyMuPDF) 與預設輸出目錄 "output"
exactpdfgrid("input.pdf")
```

也可以使用匯出的引擎常數（避免拼字錯誤）：

```python
import exactpdfgrid
from exactpdfgrid import PYMUPDF, RAPIDOCR

exactpdfgrid("input.pdf", RAPIDOCR, "outputpath")
```

或使用顯式的 `run()` 函式（功能相同，無 module-callable 魔法）：

```python
from exactpdfgrid import run, RAPIDOCR
run("input.pdf", RAPIDOCR, "outputpath")
```

Shorthand 也支援額外 keyword 參數，會直接透傳給 `process_pdf`：

```python
from exactpdfgrid import DetectionConfig
exactpdfgrid("input.pdf", "rapidocr", "out/", detection=DetectionConfig(dpi=300))
```

### 完整 API（`process_pdf`）

最小可用例：

```python
from exactpdfgrid import process_pdf

process_pdf("input.pdf", out_dir="output")
```

完整客製：

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
)
ext = ExtractionConfig(
    engine="rapidocr",            # or "pymupdf" (default)
    padding_px=3,
    clean_pipeline=[
        normalize_whitespace,
        strip_square_brackets,    # 移除 [註記]
        split_at_first_paren,     # 只保留第一個 "(" 之前的內容
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
print(f"saved: {xlsx_path}")
```

### 自訂 cleaner

任何 `Callable[[str], str]` 都可以加入 `clean_pipeline`：

```python
def lower_and_strip(s: str) -> str:
    return s.strip().lower()

ext = ExtractionConfig(clean_pipeline=[normalize_whitespace, lower_and_strip])
```

### 自訂 TextExtractor

繼承 `TextExtractor` 即可接上自家 OCR/抽取邏輯：

```python
from exactpdfgrid import TextExtractor

class MyExtractor(TextExtractor):
    name = "mine"
    def extract(self, *, fitz_page, image, cell, dpi, padding_px) -> str:
        ...  # 回傳該 cell 的原始文字

ext = ExtractionConfig(engine=MyExtractor())
```

---

## Web 介面

```powershell
exactpdfgrid-web
# 或：python -m exactpdfgrid.web.server
```

開啟 `http://localhost:5000`，拖放 PDF 即可下載 Excel。

---

## 套件結構

```
src/exactpdfgrid/
├── __init__.py          # 公開 API re-exports
├── config.py            # DetectionConfig / ExtractionConfig / OutputConfig
├── pdf_render.py        # PDF → image
├── detection.py         # 線段偵測與 cell grid 建構
├── extraction.py        # 引擎無關的文字抽取編排
├── engines/
│   ├── base.py          # TextExtractor ABC
│   ├── pymupdf.py       # 預設後端
│   └── rapidocr.py      # 選用 OCR 後端
├── utils.py             # clean_text_pipeline + 內建 cleaners
├── core.py              # process_pdf 高階入口
├── output.py            # xlsx 寫出
├── cli.py               # exactpdfgrid console script
└── web/
    ├── server.py        # exactpdfgrid-web console script
    └── static/          # index.html / app.js / style.css
```

---

## 授權

MIT。
