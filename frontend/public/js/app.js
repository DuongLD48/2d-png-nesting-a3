// NESTING Frontend Controller - Red Broadcast Design System
let currentConfig = null;
let processingJobs = {};

// Toast helper
function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = 'toast show';
  if (type === 'success') {
    toast.style.borderColor = 'var(--success-color)';
  } else if (type === 'error') {
    toast.style.borderColor = 'var(--danger-color)';
  } else {
    toast.style.borderColor = 'var(--border-color)';
  }

  setTimeout(() => {
    toast.className = 'toast';
  }, 3500);
}

// Log Terminal Helpers
function appendLog(msg) {
  const term = document.getElementById('log-terminal');
  if (!term) return;
  const timeStr = new Date().toLocaleTimeString('vi-VN');
  const div = document.createElement('div');
  div.className = 'log-entry';
  div.innerHTML = `<span class="log-time">[${timeStr}]</span> ${escapeHTML(msg)}`;
  term.appendChild(div);
  term.scrollTop = term.scrollHeight;
}

function clearLogs() {
  const term = document.getElementById('log-terminal');
  if (term) {
    term.innerHTML = '<div class="log-entry"><span class="log-time">[SYSTEM]</span> Đã dọn sạch màn hình console. Sẵn sàng nhận lệnh in mới.</div>';
  }
}

function escapeHTML(str) {
  return String(str ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Navigation Tabs
function switchTab(tabId, btn) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

  const targetTab = document.getElementById(tabId);
  if (targetTab) targetTab.classList.add('active');
  if (btn) btn.classList.add('active');

  if (tabId === 'tab-history') {
    refreshHistory();
  }
}

// Check Backend Health
async function checkBackendHealth() {
  const badge = document.getElementById('backend-status-badge');
  try {
    const res = await fetch('/api/health');
    if (res.ok) {
      const data = await res.json();
      badge.className = 'status-badge status-online';
      badge.innerHTML = '<iconify-icon icon="lucide:server" width="14"></iconify-icon> Backend Node.js Connected';
    } else {
      throw new Error(`HTTP ${res.status}`);
    }
  } catch (err) {
    badge.className = 'status-badge status-error';
    badge.innerHTML = '<iconify-icon icon="lucide:server-off" width="14"></iconify-icon> Backend Offline';
  }
}

// Fetch & Load System Config
async function loadConfigFromServer() {
  try {
    const resp = await fetch('/api/config');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    currentConfig = await resp.json();

    // Populate Settings Tab Form
    document.getElementById('cfg-anhlocal').value = currentConfig.anhlocal_dir || '';
    document.getElementById('cfg-output').value = currentConfig.output_dir || '';
    document.getElementById('lbl-anhlocal').textContent = currentConfig.anhlocal_dir || 'ANHLOCAL';
    document.getElementById('lbl-output').textContent = currentConfig.output_dir || 'output';

    const custom = currentConfig.custom_nesting || {};
    document.getElementById('custom-paper-size').value = custom.paper_size || 'Custom (390x290mm)';
    document.getElementById('custom-width-mm').value = custom.width_mm || 390;
    document.getElementById('custom-height-mm').value = custom.height_mm || 290;
    document.getElementById('custom-dpi').value = custom.dpi || 300;
    document.getElementById('custom-padding-mm').value = custom.padding_mm || 3;

    const pet = currentConfig.pet_nesting || {};
    document.getElementById('pet-paper-size').value = pet.paper_size || 'PET Roll (580x1000mm)';
    document.getElementById('pet-width-mm').value = pet.width_mm || 580;
    document.getElementById('pet-height-mm').value = pet.height_mm || 1000;
    document.getElementById('pet-dpi').value = pet.dpi || 300;
    document.getElementById('pet-padding-mm').value = pet.padding_mm || 5;

    const fb = currentConfig.firebase || {};
    document.getElementById('cfg-fb-project').value = fb.projectId || 'order-web-hoang';
    document.getElementById('cfg-fb-key').value = fb.apiKey || '';

    // Initialize Client Firebase sync if available
    if (fb.apiKey && fb.projectId && window.initClientFirebaseSync) {
      window.initClientFirebaseSync(fb);
    }
  } catch (e) {
    appendLog(`❌ Lỗi tải cấu hình từ Backend: ${e.message}`);
  }
}

// Save System Config
async function saveConfigToServer() {
  if (!currentConfig) currentConfig = {};

  const updatedCfg = {
    ...currentConfig,
    anhlocal_dir: document.getElementById('cfg-anhlocal').value.trim(),
    output_dir: document.getElementById('cfg-output').value.trim(),
    custom_nesting: {
      ...currentConfig.custom_nesting,
      paper_size: document.getElementById('custom-paper-size').value,
      width_mm: parseFloat(document.getElementById('custom-width-mm').value),
      height_mm: parseFloat(document.getElementById('custom-height-mm').value),
      dpi: parseInt(document.getElementById('custom-dpi').value, 10),
      padding_mm: parseFloat(document.getElementById('custom-padding-mm').value)
    },
    pet_nesting: {
      ...currentConfig.pet_nesting,
      paper_size: document.getElementById('pet-paper-size').value,
      width_mm: parseFloat(document.getElementById('pet-width-mm').value),
      height_mm: parseFloat(document.getElementById('pet-height-mm').value),
      dpi: parseInt(document.getElementById('pet-dpi').value, 10),
      padding_mm: parseFloat(document.getElementById('pet-padding-mm').value)
    },
    firebase: {
      ...currentConfig.firebase,
      projectId: document.getElementById('cfg-fb-project').value.trim(),
      apiKey: document.getElementById('cfg-fb-key').value.trim(),
      auto_listen: true
    }
  };

  try {
    const resp = await fetch('/api/save_config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updatedCfg)
    });

    const res = await resp.json();
    if (res.success) {
      currentConfig = updatedCfg;
      document.getElementById('lbl-anhlocal').textContent = updatedCfg.anhlocal_dir;
      document.getElementById('lbl-output').textContent = updatedCfg.output_dir;
      showToast('✅ Đã lưu cấu hình vào local_config.json thành công!', 'success');
      appendLog('✅ Đã lưu cấu hình hệ thống thành công.');
    } else {
      showToast('❌ Lỗi khi lưu cấu hình!', 'error');
    }
  } catch (err) {
    showToast(`❌ Lỗi kết nối server: ${err.message}`, 'error');
  }
}

// Execute Print Job via Backend API
async function executeJob(jobData) {
  const jobId = jobData.id || `JOB-${Date.now()}`;
  appendLog(`▶️ [JOB START] Kích hoạt Job: ${jobId} | Order: "${jobData.order_id || 'N/A'}" | Loại: ${jobData.job_type}`);

  try {
    const resp = await fetch('/api/process_job', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(jobData)
    });

    const result = await resp.json();

    if (result.logs && Array.isArray(result.logs)) {
      result.logs.forEach(l => appendLog(l));
    }

    if (result.status === 'completed') {
      showToast(`🎉 Hoàn thành xử lý Job ${jobId}!`, 'success');
      appendLog(`✅ [JOB FINISHED] Thư mục kết quả: ${result.relative_folder || result.job_output_folder}`);
      refreshHistory();
    } else {
      showToast(`⚠️ Xảy ra lỗi khi chạy Job: ${result.message || 'Unknown error'}`, 'error');
    }
    return result;
  } catch (err) {
    appendLog(`❌ Lỗi gọi API /api/process_job: ${err.message}`);
    showToast(`❌ Lỗi thực thi: ${err.message}`, 'error');
    throw err;
  }
}

// Manual Job Trigger
async function runManualJob() {
  const orderId = document.getElementById('manual-order-id').value.trim();
  const skusRaw = document.getElementById('manual-skus').value.trim();
  const jobType = document.getElementById('manual-job-type').value;

  const skus = skusRaw.split(',').map(s => s.trim()).filter(Boolean);

  if (skus.length === 0) {
    showToast('⚠️ Vui lòng nhập ít nhất 1 mã SKU!', 'error');
    return;
  }

  const payload = {
    id: `MANUAL-${Date.now()}`,
    order_id: orderId,
    skus: skus,
    job_type: jobType
  };

  const btn = document.getElementById('btn-run-manual');
  btn.disabled = true;
  btn.innerHTML = '<iconify-icon icon="lucide:loader-2" class="spin" width="16"></iconify-icon> Đang xử lý Nesting...';

  try {
    await executeJob(payload);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<iconify-icon icon="lucide:play" width="16"></iconify-icon> Bắt Đầu Xếp Khổ / Xuất Ảnh';
  }
}

// Refresh Output History Gallery
async function refreshHistory() {
  const container = document.getElementById('history-container');
  if (!container) return;

  container.innerHTML = '<p style="color: var(--text-secondary);"><iconify-icon icon="lucide:loader" class="spin"></iconify-icon> Đang quét thư mục kết quả output/...</p>';

  try {
    const resp = await fetch('/api/history');
    const folders = await resp.json();

    if (!folders || folders.length === 0) {
      container.innerHTML = '<p style="color: var(--text-secondary);">Chưa có thư mục kết quả Print Job nào trong output/.</p>';
      return;
    }

    let html = '<div class="gallery-grid">';
    folders.forEach(f => {
      const summary = f.summary || {};
      const orderIds = summary.order_ids || 'N/A';
      const jobType = (summary.job_type || 'Nesting').toUpperCase();

      html += `
        <div class="gallery-card">
          <div class="gallery-card-header">
            <iconify-icon icon="lucide:folder-archive" width="48" style="color: var(--primary);"></iconify-icon>
          </div>
          <div class="gallery-card-body">
            <div>
              <div class="gallery-title">${escapeHTML(f.name)}</div>
              <div class="gallery-meta"><strong>Đơn hàng:</strong> ${escapeHTML(orderIds)}</div>
              <div class="gallery-meta"><strong>Tác vụ:</strong> <span class="brand-badge" style="font-size: 10px; padding: 2px 6px;">${escapeHTML(jobType)}</span></div>
              <div class="gallery-meta"><strong>Tổng file:</strong> ${f.file_count} files (${f.png_count} ảnh PNG output)</div>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 6px; word-break: break-all;">${escapeHTML(f.path)}</div>
            </div>
            <div class="gallery-actions">
              ${f.png_files && f.png_files.length > 0 ? `
                <button class="btn btn-primary btn-sm" onclick="previewImage('${escapeHTML(f.name)}', '${escapeHTML(f.png_files[0])}')">
                  <iconify-icon icon="lucide:eye" width="14"></iconify-icon> Xem Ảnh
                </button>
              ` : ''}
              <button class="btn btn-secondary btn-sm" onclick="showFolderInfo('${escapeHTML(f.name)}', ${f.file_count})">
                <iconify-icon icon="lucide:info" width="14"></iconify-icon> Chi Tiết
              </button>
            </div>
          </div>
        </div>
      `;
    });
    html += '</div>';
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<p style="color: var(--danger-color);">Lỗi tải lịch sử thư mục: ${err.message}</p>`;
  }
}

// Image Preview Modal
function previewImage(folder, filename) {
  const modal = document.getElementById('preview-modal');
  const title = document.getElementById('modal-title');
  const body = document.getElementById('modal-body');

  title.textContent = `Xem Trước: ${folder} / ${filename}`;
  const imgUrl = `/api/output/${encodeURIComponent(folder)}/${encodeURIComponent(filename)}`;

  body.innerHTML = `
    <img src="${imgUrl}" class="modal-img" alt="Rendered Preview" />
    <div style="margin-top: 14px;">
      <a href="${imgUrl}" target="_blank" download class="btn btn-primary btn-sm">
        <iconify-icon icon="lucide:download" width="14"></iconify-icon> Tải Ảnh Gốc Về Máy
      </a>
    </div>
  `;

  modal.classList.add('open');
}

function showFolderInfo(folder, fileCount) {
  showToast(`📁 Thư mục "${folder}" chứa ${fileCount} files`, 'info');
}

function closeModal() {
  document.getElementById('preview-modal').classList.remove('open');
}

// Global Exports for inline DOM events
window.switchTab = switchTab;
window.runManualJob = runManualJob;
window.saveConfigToServer = saveConfigToServer;
window.refreshHistory = refreshHistory;
window.clearLogs = clearLogs;
window.previewImage = previewImage;
window.showFolderInfo = showFolderInfo;
window.closeModal = closeModal;
window.appendLog = appendLog;
window.executeJob = executeJob;

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  loadConfigFromServer();
  checkBackendHealth();
  setInterval(checkBackendHealth, 10000);
});
