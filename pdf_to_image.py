"""
Step 1: Render each PDF page to a high-resolution numpy image (BGR, for OpenCV).
"""

from pathlib import Path
import numpy as np
import fitz  # PyMuPDF
import cv2


def pdf_to_images(pdf_path: str, dpi: int = 200) -> list[np.ndarray]:
    """
    Open a PDF and render every page at `dpi` dots-per-inch.

    Returns
    -------
    list[np.ndarray]
        One BGR image per page, suitable for OpenCV processing.
    """
    doc = fitz.open(pdf_path)
    scale = dpi / 72.0
    mat = fitz.Matrix(scale, scale)

    images: list[np.ndarray] = []
    for page_index, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
        # pix.samples is a bytes object: H × W × 3  (RGB)
        img_rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, 3
        )
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        images.append(img_bgr)
        print(f"  [pdf_to_image] page {page_index + 1}: {pix.width}×{pix.height} px")

    doc.close()
    return images


def save_page_images(images: list[np.ndarray], out_dir: str = "output/images") -> list[str]:
    """Save page images to disk and return their paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, img in enumerate(images):
        p = str(out / f"page_{i + 1:03d}.png")
        cv2.imwrite(p, img)
        paths.append(p)
    return paths
