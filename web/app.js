(() => {
  const pdfFile      = document.getElementById('pdfFile');
  const uploadArea   = document.getElementById('pdfUploadArea');
  const fileNameEl   = document.getElementById('fileName');
  const convertBtn   = document.getElementById('convertBtn');
  const statusEl     = document.getElementById('status');
  const advToggle    = document.getElementById('advToggle');
  const advPanel     = document.getElementById('advPanel');

  // ── Advanced panel toggle ──────────────────────────────────────────────
  const toggleAdv = () => {
    const open = advPanel.classList.toggle('collapsed') === false;
    advToggle.classList.toggle('open', open);
  };

  advToggle.addEventListener('click', toggleAdv);
  advToggle.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') toggleAdv(); });

  // ── Upload area: click to open file picker ─────────────────────────────
  uploadArea.addEventListener('click', () => pdfFile.click());

  pdfFile.addEventListener('change', () => {
    if (pdfFile.files.length) showFile(pdfFile.files[0]);
  });

  // ── Drag and drop ──────────────────────────────────────────────────────
  uploadArea.addEventListener('dragover', e => {
    e.preventDefault();
    uploadArea.classList.add('dragging-over');
  });

  ['dragleave', 'dragend'].forEach(ev =>
    uploadArea.addEventListener(ev, () => uploadArea.classList.remove('dragging-over'))
  );

  uploadArea.addEventListener('drop', e => {
    e.preventDefault();
    uploadArea.classList.remove('dragging-over');
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
      showFile(file);
      // Inject into the hidden input
      const dt = new DataTransfer();
      dt.items.add(file);
      pdfFile.files = dt.files;
    } else {
      setStatus('請拖放有效的 PDF 檔案', 'error');
    }
  });

  function showFile(file) {
    fileNameEl.textContent = file.name;
    fileNameEl.classList.add('active');
    uploadArea.querySelector('.upload-text').textContent = '已選擇檔案';
    clearStatus();
  }

  // ── Convert & download ─────────────────────────────────────────────────
  convertBtn.addEventListener('click', async () => {
    if (!pdfFile.files.length) {
      setStatus('請先選擇 PDF 檔案', 'error');
      return;
    }

    const file = pdfFile.files[0];
    const formData = new FormData();
    formData.append('pdf',           file);
    formData.append('dpi',           document.getElementById('dpi').value);
    formData.append('min_line',      document.getElementById('minLine').value);
    formData.append('ink_threshold', document.getElementById('inkThreshold').value);
    formData.append('cluster_gap',   document.getElementById('clusterGap').value);

    convertBtn.disabled = true;
    setStatus('<span class="spinner"></span>轉換中，請稍候…', 'loading');

    try {
      const resp = await fetch('/convert', { method: 'POST', body: formData });

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({ error: `HTTP ${resp.status}` }));
        throw new Error(data.error || `HTTP ${resp.status}`);
      }

      const blob = await resp.blob();

      // Derive filename from Content-Disposition or use the original PDF name
      let filename = file.name.replace(/\.pdf$/i, '.xlsx');
      const cd = resp.headers.get('Content-Disposition') || '';
      const m  = cd.match(/filename\*?=(?:UTF-8'')?["']?([^"';\r\n]+)/i);
      if (m) filename = decodeURIComponent(m[1]);

      // Trigger download
      const url = URL.createObjectURL(blob);
      const a   = document.createElement('a');
      a.href     = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      setStatus(`✅ 已完成！下載 <strong>${filename}</strong>`, '');
    } catch (err) {
      setStatus(`❌ 錯誤：${err.message}`, 'error');
    } finally {
      convertBtn.disabled = false;
    }
  });

  // ── Helpers ────────────────────────────────────────────────────────────
  function setStatus(html, cls) {
    statusEl.innerHTML = html;
    statusEl.className = 'status' + (cls ? ` ${cls}` : '');
  }

  function clearStatus() {
    statusEl.innerHTML = '';
    statusEl.className = 'status';
  }
})();
