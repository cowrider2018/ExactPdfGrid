# ExactPdfGrid

ExactPdfGrid 是一個 PDF 表格偵測與匯出工具，能從 PDF 頁面中辨識表格線段、重建儲存格格線，並匯出為 Excel（.xlsx）。本專案提供 CLI 與 Web 介面。

需求
- Windows / macOS / Linux
- Python 3.8+

一鍵啟動 Web 介面
- 已在專案根目錄新增 `start.bat`，雙擊即可：
  - 建立 `.venv`（若不存在）
  - 安裝 `requirements.txt` 中套件
  - 啟動 Flask 伺服器（執行 `server.py`）
  - 自動開啟瀏覽器到 `http://localhost:5000`
  - 可透過拖放上傳 PDF，伺服器會回傳並自動下載 Excel 檔案。

命令列（CLI）使用
- 使用 `main.py` 可對單一 PDF 或資料夾批次處理：

```powershell
python main.py input.pdf
```

輸出
- 預設輸出路徑為 `output/<pdf_stem>.xlsx`，每個 PDF 的每一頁各成一個工作表。

授權
- 本專案採用 MIT 授權（如需其他授權請提出）