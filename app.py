import os
import json
import http.server
import socketserver
import urllib.parse
import urllib.request
import traceback
import threading
import datetime
import time
import shutil

from src.job_runner import load_local_config, save_local_config, run_job_execution

PORT = 8000
EXECUTION_LOGS = []

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Red Broadcast - Local Nesting & Firebase Monitor</title>
    <!-- Google Fonts: Roboto & Roboto Mono per DESIGN.md -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500;700&family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
    <script src="https://code.iconify.design/iconify-icon/1.0.7/iconify-icon.min.js"></script>
    
    <!-- Firebase 10 SDK via ESM -->
    <script type="module">
        import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js';
        import { getFirestore, collection, onSnapshot, doc, updateDoc, serverTimestamp } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js';

        window.initLocalFirebaseSync = function(config) {
            if (!config || !config.apiKey || !config.projectId) {
                console.log('[Local App] Firebase config missing, running in standalone mode.');
                document.getElementById('fb-sync-status').className = 'status-badge status-offline';
                document.getElementById('fb-sync-status').innerHTML = '🔴 Standby (Chờ Lệnh Manual / API)';
                return;
            }

            try {
                const app = initializeApp(config);
                const db = getFirestore(app);
                document.getElementById('fb-sync-status').className = 'status-badge status-online';
                document.getElementById('fb-sync-status').innerHTML = '🟢 Firebase Sync Realtime Active';

                // Listen to print_jobs collection in real-time
                const jobsRef = collection(db, 'print_jobs');
                onSnapshot(jobsRef, (snapshot) => {
                    snapshot.docChanges().forEach((change) => {
                        if (change.type === 'added' || change.type === 'modified') {
                            const jobData = { id: change.doc.id, ...change.doc.data() };
                            if (jobData.status === 'pending' && !window.processingJobs[jobData.id]) {
                                window.processingJobs[jobData.id] = true;
                                console.log('[Firebase Realtime] Nhận Print Job mới:', jobData);
                                window.executeJobLocal(jobData, db);
                            }
                        }
                    });
                }, (err) => {
                    console.error('[Firebase Listener Error]', err);
                    document.getElementById('fb-sync-status').className = 'status-badge status-offline';
                    document.getElementById('fb-sync-status').innerHTML = '⚠️ Firebase Error: ' + err.message;
                });
            } catch (e) {
                console.error('[Firebase Init Error]', e);
            }
        };

        window.processingJobs = {};

        window.executeJobLocal = async function(jobData, db) {
            window.appendLog(`📥 [FIREBASE REALTIME] Nhận lệnh Print Job: ${jobData.id} (Order: ${jobData.order_id || 'N/A'})`);
            
            try {
                // Call local backend processing API
                const resp = await fetch('/api/process_job', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(jobData)
                });

                const result = await resp.json();
                
                if (result.logs && Array.isArray(result.logs)) {
                    result.logs.forEach(l => window.appendLog(l));
                }

                if (result.status === 'completed' && db) {
                    // Update Print Job Status in Firestore
                    const jobRef = doc(db, 'print_jobs', jobData.id);
                    await updateDoc(jobRef, {
                        status: 'completed',
                        completed_at: new Date().toISOString(),
                        output_folder: result.relative_folder || '',
                        updatedAt: serverTimestamp()
                    });

                    // Update Order POD Print Status to 'completed' in Firestore
                    if (jobData.order_id) {
                        const orderIds = String(jobData.order_id).split(',').map(s => s.trim()).filter(Boolean);
                        for (const oid of orderIds) {
                            try {
                                const orderRef = doc(db, 'MACCHOVUI', oid);
                                await setDoc(orderRef, {
                                    pod_print_status: 'completed',
                                    pod_print_status_text: 'Đã hoàn thành in',
                                    fulfillment_status_text: 'Hoàn thành in',
                                    sku_processed: true,
                                    updatedAt: serverTimestamp()
                                }, { merge: true });
                            } catch (e1) {
                                try {
                                    const fallbackRef = doc(db, 'orders', oid);
                                    await setDoc(fallbackRef, {
                                        pod_print_status: 'completed',
                                        pod_print_status_text: 'Đã hoàn thành in',
                                        fulfillment_status_text: 'Hoàn thành in',
                                        sku_processed: true,
                                        updatedAt: serverTimestamp()
                                    }, { merge: true });
                                } catch (e2) {}
                            }
                        }
                    }

                    window.appendLog(`✅ [FIREBASE UPDATE] Đã tick hoàn thành trên Web & chuyển Trạng Thái POD đơn ${jobData.order_id} sang "Đã hoàn thành in"!`);
                    window.refreshHistory();
                }
            } catch (err) {
                window.appendLog(`❌ Lỗi thực thi local: ${err.message}`);
            } finally {
                delete window.processingJobs[jobData.id];
            }
        };
    </script>

    <style>
        /* Red Broadcast Design System per DESIGN.md */
        :root {
            --primary: #FF0000;
            --primary-hover: #CC0000;
            --secondary-link: #065FD4;
            --neutral-gray: #606060;
            --bg-main: #0F0F0F;
            --surface-panel: #1E293B;
            --surface-card: #181818;
            --text-primary: #FFFFFF;
            --text-secondary: #AAAAAA;
            --border-color: #272727;
            --success-color: #2BA640;
            --warning-color: #FB8C00;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Roboto', sans-serif; }
        body { background-color: var(--bg-main); color: var(--text-primary); padding-bottom: 40px; }

        /* Top Bar 56px per DESIGN.md */
        header.top-bar {
            height: 56px; background-color: #0F0F0F; border-bottom: 1px solid var(--border-color);
            display: flex; align-items: center; justify-content: space-between; padding: 0 24px;
            position: sticky; top: 0; z-index: 100;
        }

        .brand-logo { display: flex; align-items: center; gap: 10px; text-decoration: none; color: #FFF; font-weight: 700; font-size: 18px; }
        .brand-badge { background: var(--primary); color: #FFF; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 700; text-transform: uppercase; }

        .status-badge { font-size: 13px; font-weight: 500; padding: 4px 12px; border-radius: 9999px; display: inline-flex; align-items: center; gap: 6px; }
        .status-online { background: rgba(43, 166, 64, 0.15); color: #2BA640; border: 1px solid rgba(43, 166, 64, 0.3); }
        .status-offline { background: rgba(251, 140, 0, 0.15); color: #FB8C00; border: 1px solid rgba(251, 140, 0, 0.3); }

        /* Navigation Tab Bar */
        .tab-bar { display: flex; gap: 8px; padding: 16px 24px; border-bottom: 1px solid var(--border-color); background: #121212; }
        .tab-btn {
            background: transparent; color: var(--text-secondary); border: none; padding: 10px 18px;
            font-size: 14px; font-weight: 500; border-radius: 9999px; cursor: pointer; transition: all 0.2s;
            display: inline-flex; align-items: center; gap: 8px;
        }
        .tab-btn:hover { background: rgba(255,255,255,0.08); color: #FFF; }
        .tab-btn.active { background: var(--primary); color: #FFF; font-weight: 700; }

        /* Container & Grid Layout */
        .main-container { max-width: 1400px; margin: 24px auto; padding: 0 24px; }
        .grid-2col { display: grid; grid-template-columns: 1fr 420px; gap: 24px; }

        .card-panel {
            background: var(--surface-card); border: 1px solid var(--border-color); border-radius: 12px;
            padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); margin-bottom: 24px;
        }

        .panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--border-color); }
        .panel-title { font-size: 18px; font-weight: 700; color: #FFF; display: flex; align-items: center; gap: 8px; }

        /* Form Controls */
        .form-group { margin-bottom: 16px; }
        .form-label { display: block; font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px; }
        .form-control {
            width: 100%; background: #080808; border: 1px solid var(--border-color); color: #FFF;
            padding: 10px 14px; border-radius: 8px; font-size: 14px; font-family: 'Roboto', sans-serif;
            transition: border 0.2s;
        }
        .form-control:focus { outline: none; border-color: var(--primary); }
        textarea.form-control { font-family: 'Roboto Mono', monospace; font-size: 12px; min-height: 100px; }

        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

        /* Buttons per DESIGN.md */
        .btn-primary {
            background: var(--primary); color: #FFF; border: none; font-weight: 700; padding: 12px 20px;
            border-radius: 9999px; cursor: pointer; font-size: 14px; transition: background 0.2s;
            display: inline-flex; align-items: center; justify-content: center; gap: 8px; width: 100%;
        }
        .btn-primary:hover { background: var(--primary-hover); }

        .btn-secondary {
            background: rgba(255,255,255,0.1); color: #FFF; border: 1px solid var(--border-color);
            font-weight: 500; padding: 10px 16px; border-radius: 9999px; cursor: pointer; font-size: 13px;
        }
        .btn-secondary:hover { background: rgba(255,255,255,0.2); }

        /* Live Log Terminal Stream Console */
        .log-terminal {
            background: #050505; border: 1px solid #222; border-radius: 8px; padding: 14px;
            font-family: 'Roboto Mono', monospace; font-size: 12px; color: #4ADE80;
            height: 480px; overflow-y: auto; line-height: 1.6; white-space: pre-wrap;
        }

        .log-entry { margin-bottom: 4px; }
        .log-time { color: var(--text-secondary); margin-right: 8px; }

        /* Gallery Grid */
        .gallery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-top: 16px; }
        .gallery-card { background: #0A0A0A; border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; }
        .gallery-card img { width: 100%; height: 220px; object-fit: contain; background: #000; border-bottom: 1px solid var(--border-color); }
        .gallery-info { padding: 12px; font-size: 13px; }

        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>

    <!-- Header (56px per DESIGN.md) -->
    <header class="top-bar">
        <div style="display: flex; align-items: center; gap: 16px;">
            <a href="#" class="brand-logo">
                <iconify-icon icon="lucide:radio-tower" width="24" style="color: var(--primary);"></iconify-icon>
                RED BROADCAST <span class="brand-badge">LOCAL APP</span>
            </a>
            <span style="font-size: 13px; color: var(--text-secondary);">Hệ Thống Lắng Nghe Firebase & Tự Động Xếp Khổ Nesting</span>
        </div>
        <div>
            <span id="fb-sync-status" class="status-badge status-offline">Đang khởi tạo...</span>
        </div>
    </header>

    <!-- Sub Navigation Tabs -->
    <div class="tab-bar">
        <button class="tab-btn active" onclick="switchTab('tab-dashboard', this)">
            <iconify-icon icon="lucide:activity" width="16"></iconify-icon> Dashboard & Log Stream
        </button>
        <button class="tab-btn" onclick="switchTab('tab-settings', this)">
            <iconify-icon icon="lucide:settings" width="16"></iconify-icon> Cấu Hình Settings (Đường Dẫn & Khổ In)
        </button>
        <button class="tab-btn" onclick="switchTab('tab-history', this)">
            <iconify-icon icon="lucide:folder-check" width="16"></iconify-icon> Lịch Sử Print Jobs & Result Folders
        </button>
    </div>

    <div class="main-container">

        <!-- TAB 1: DASHBOARD & LOG STREAM -->
        <div id="tab-dashboard" class="tab-content active">
            <div class="grid-2col">
                <div>
                    <div class="card-panel">
                        <div class="panel-header">
                            <span class="panel-title">
                                <iconify-icon icon="lucide:terminal" width="20" style="color: var(--primary);"></iconify-icon>
                                Nhật Ký Thực Thi Real-time (Live Execution Stream Log)
                            </span>
                            <button class="btn-secondary" onclick="clearLogs()">Clear Console</button>
                        </div>
                        <div class="log-terminal" id="log-terminal">
<div class="log-entry"><span class="log-time">[SYSTEM]</span> Đã khởi chạy Local WebApp Engine trên port 8000...</div>
<div class="log-entry"><span class="log-time">[SYSTEM]</span> Sẵn sàng lắng nghe lệnh Print Job từ Web QUAN LY DON qua Firebase / API!</div>
                        </div>
                    </div>
                </div>

                <div>
                    <div class="card-panel">
                        <div class="panel-header">
                            <span class="panel-title">
                                <iconify-icon icon="lucide:play-circle" width="20" style="color: var(--primary);"></iconify-icon>
                                Test Lệnh Manual (Local Run)
                            </span>
                        </div>
                        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 14px;">Chạy thử thủ công một Print Job với danh sách SKU mẫu (Ví dụ: 03-D-XL, 01-T-M):</p>
                        
                        <div class="form-group">
                            <label class="form-label">Mã Đơn Hàng Mẫu:</label>
                            <input type="text" id="manual-order-id" class="form-control" value="TEST-ORDER-1001">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Danh sách SKU (Phân cách bằng dấu phẩy):</label>
                            <input type="text" id="manual-skus" class="form-control" value="03-D-XL, 01-T-M">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Loại Thao Tác Quy Trình:</label>
                            <select id="manual-job-type" class="form-control">
                                <option value="custom_nesting">1. Xếp Khổ Custom</option>
                                <option value="dtg">2. In DTG (Chỉ Copy Ảnh)</option>
                                <option value="pet_nesting">3. Xếp Khổ PET</option>
                            </select>
                        </div>

                        <button class="btn-primary" onclick="runManualJob()">
                            <iconify-icon icon="lucide:play" width="18"></iconify-icon>
                            Chạy Thử Quy Trình Local
                        </button>
                    </div>

                    <div class="card-panel">
                        <div class="panel-header">
                            <span class="panel-title">
                                <iconify-icon icon="lucide:folder-git-2" width="20" style="color: #38BDF8;"></iconify-icon>
                                Đường Dẫn Hệ Thống
                            </span>
                        </div>
                        <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.8;">
                            <p><strong>📁 Thư mục ANHLOCAL gốc:</strong> <br><code id="lbl-anhlocal" style="color: #38BDF8;">{ANHLOCAL_DIR}</code></p>
                            <p style="margin-top: 10px;"><strong>📂 Thư mục Output cách ly:</strong> <br><code id="lbl-output" style="color: #4ADE80;">{OUTPUT_DIR}</code></p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 2: SETTINGS (ĐƯỜNG DẪN & CẤU HÌNH KHỔ IN) -->
        <div id="tab-settings" class="tab-content">
            <div class="card-panel">
                <div class="panel-header">
                    <span class="panel-title">
                        <iconify-icon icon="lucide:folder-tree" width="20" style="color: var(--primary);"></iconify-icon>
                        1. Thư Mục Chứa Ảnh Gốc & Thư Mục Đích Cấu Hình (Lưu File JSON)
                    </span>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Đường Dẫn Tuyệt Đối Thư Mục Ảnh Gốc (ANHLOCAL):</label>
                    <input type="text" id="cfg-anhlocal" class="form-control" value="{ANHLOCAL_DIR}">
                    <small style="color: var(--text-secondary); font-size: 12px; margin-top: 4px; display: block;">Ví dụ: <code>E:\\FINAL\\Anh-Hoang\\AUTO-MACCHOVUI\\NESTING\\ANHLOCAL</code></small>
                </div>

                <div class="form-group">
                    <label class="form-label">Đường Dẫn Tuyệt Đối Thư Mục Đích Xuất File (OUTPUT):</label>
                    <input type="text" id="cfg-output" class="form-control" value="{OUTPUT_DIR}">
                    <small style="color: var(--text-secondary); font-size: 12px; margin-top: 4px; display: block;">Mỗi lệnh Print Job hệ thống sẽ tự động tạo 1 folder cách ly riêng biệt bên trong thư mục này.</small>
                </div>
            </div>

            <div class="grid-2col">
                <div class="card-panel">
                    <div class="panel-header">
                        <span class="panel-title">
                            <iconify-icon icon="lucide:sliders" width="20" style="color: var(--primary);"></iconify-icon>
                            2. Cấu Hình Xếp Khổ CUSTOM
                        </span>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Tên Khổ Giấy / Giới Thiệu:</label>
                        <input type="text" id="custom-paper-size" class="form-control" value="{CUSTOM_PAPER_SIZE}">
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label class="form-label">Chiều Rộng (mm):</label>
                            <input type="number" step="0.1" id="custom-width-mm" class="form-control" value="{CUSTOM_WIDTH_MM}">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Chiều Cao (mm):</label>
                            <input type="number" step="0.1" id="custom-height-mm" class="form-control" value="{CUSTOM_HEIGHT_MM}">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label class="form-label">DPI Render:</label>
                            <input type="number" id="custom-dpi" class="form-control" value="{CUSTOM_DPI}">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Khoảng Cách Padding (mm):</label>
                            <input type="number" step="0.1" id="custom-padding-mm" class="form-control" value="{CUSTOM_PADDING_MM}">
                        </div>
                    </div>
                </div>

                <div class="card-panel">
                    <div class="panel-header">
                        <span class="panel-title">
                            <iconify-icon icon="lucide:layers" width="20" style="color: #38BDF8;"></iconify-icon>
                            3. Cấu Hình Xếp Khổ PET
                        </span>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Tên Khổ Cuộn PET:</label>
                        <input type="text" id="pet-paper-size" class="form-control" value="{PET_PAPER_SIZE}">
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label class="form-label">Chiều Rộng (mm):</label>
                            <input type="number" step="0.1" id="pet-width-mm" class="form-control" value="{PET_WIDTH_MM}">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Chiều Cao (mm):</label>
                            <input type="number" step="0.1" id="pet-height-mm" class="form-control" value="{PET_HEIGHT_MM}">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label class="form-label">DPI Render:</label>
                            <input type="number" id="pet-dpi" class="form-control" value="{PET_DPI}">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Khoảng Cách Padding (mm):</label>
                            <input type="number" step="0.1" id="pet-padding-mm" class="form-control" value="{PET_PADDING_MM}">
                        </div>
                    </div>
                </div>
            </div>

            <div style="margin-top: 12px; text-align: right;">
                <button class="btn-primary" style="width: auto; padding: 12px 32px;" onclick="saveConfigToServer()">
                    <iconify-icon icon="lucide:save" width="18"></iconify-icon> Lưu Toàn Bộ Cấu Hình Settings
                </button>
            </div>
        </div>

        <!-- TAB 3: HISTORY & PREVIEW -->
        <div id="tab-history" class="tab-content">
            <div class="card-panel">
                <div class="panel-header">
                    <span class="panel-title">
                        <iconify-icon icon="lucide:history" width="20" style="color: var(--primary);"></iconify-icon>
                        Thư Mục Kết Quả Các Print Job Riêng Biệt
                    </span>
                    <button class="btn-secondary" onclick="refreshHistory()">Làm Mới Danh Sách</button>
                </div>
                <div id="history-container">
                    <p style="color: var(--text-secondary);">Đang tải danh sách thư mục kết quả...</p>
                </div>
            </div>
        </div>

    </div>

    <script>
        const LOCAL_CONFIG = {CONFIG_JSON_RAW};

        function switchTab(tabId, btn) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            btn.classList.add('active');

            if (tabId === 'tab-history') {
                refreshHistory();
            }
        }

        function appendLog(msg) {
            const term = document.getElementById('log-terminal');
            const timeStr = new Date().toLocaleTimeString('vi-VN');
            const div = document.createElement('div');
            div.className = 'log-entry';
            div.innerHTML = `<span class="log-time">[${timeStr}]</span> ${escapeHTML(msg)}`;
            term.appendChild(div);
            term.scrollTop = term.scrollHeight;
        }

        function clearLogs() {
            document.getElementById('log-terminal').innerHTML = '<div class="log-entry"><span class="log-time">[SYSTEM]</span> Console log format cleared. Ready for next job.</div>';
        }

        function escapeHTML(str) {
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        async function runManualJob() {
            const orderId = document.getElementById('manual-order-id').value.trim();
            const skusRaw = document.getElementById('manual-skus').value.trim();
            const jobType = document.getElementById('manual-job-type').value;

            const skus = skusRaw.split(',').map(s => s.trim()).filter(Boolean);

            const payload = {
                id: 'MANUAL-' + Date.now(),
                order_id: orderId,
                skus: skus,
                job_type: jobType
            };

            appendLog(`▶️ [MANUAL START] Đã kích hoạt chạy thử thủ công: Order "${orderId}" | SKUs: [${skus.join(', ')}]`);
            await window.executeJobLocal(payload, null);
        }

        async function saveConfigToServer() {
            const anhlocal = document.getElementById('cfg-anhlocal').value.trim();
            const output = document.getElementById('cfg-output').value.trim();

            const updatedCfg = {
                ...LOCAL_CONFIG,
                anhlocal_dir: anhlocal,
                output_dir: output,
                custom_nesting: {
                    ...LOCAL_CONFIG.custom_nesting,
                    paper_size: document.getElementById('custom-paper-size').value,
                    width_mm: parseFloat(document.getElementById('custom-width-mm').value),
                    height_mm: parseFloat(document.getElementById('custom-height-mm').value),
                    dpi: parseInt(document.getElementById('custom-dpi').value, 10),
                    padding_mm: parseFloat(document.getElementById('custom-padding-mm').value)
                },
                pet_nesting: {
                    ...LOCAL_CONFIG.pet_nesting,
                    paper_size: document.getElementById('pet-paper-size').value,
                    width_mm: parseFloat(document.getElementById('pet-width-mm').value),
                    height_mm: parseFloat(document.getElementById('pet-height-mm').value),
                    dpi: parseInt(document.getElementById('pet-dpi').value, 10),
                    padding_mm: parseFloat(document.getElementById('pet-padding-mm').value)
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
                    alert('Đã lưu cấu hình Settings vào local_config.json thành công!');
                    document.getElementById('lbl-anhlocal').textContent = anhlocal;
                    document.getElementById('lbl-output').textContent = output;
                } else {
                    alert('Lỗi lưu cấu hình!');
                }
            } catch (e) {
                alert('Lỗi kết nối server: ' + e.message);
            }
        }

        async function refreshHistory() {
            const container = document.getElementById('history-container');
            container.innerHTML = '<p style="color: var(--text-secondary);">Đang quét thư mục kết quả...</p>';

            try {
                const resp = await fetch('/api/history');
                const folders = await resp.json();

                if (!folders || folders.length === 0) {
                    container.innerHTML = '<p style="color: var(--text-secondary);">Chưa có folder kết quả Print Job nào trong output/.</p>';
                    return;
                }

                let html = '<div class="gallery-grid">';
                folders.forEach(f => {
                    html += `
                        <div class="gallery-card">
                            <div style="background: #000; padding: 12px; text-align: center;">
                                <iconify-icon icon="lucide:folder-archive" width="48" style="color: #FF0000;"></iconify-icon>
                            </div>
                            <div class="gallery-info">
                                <strong style="display: block; color: #FFF; font-size: 14px; margin-bottom: 4px; word-break: break-all;">${escapeHTML(f.name)}</strong>
                                <span style="font-size: 12px; color: var(--text-secondary); display: block;">Chứa ${f.file_count} files (${f.png_count} ảnh PNG output)</span>
                                <span style="font-size: 11px; color: #606060; margin-top: 6px; display: block;">Location: ${escapeHTML(f.path)}</span>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
                container.innerHTML = html;
            } catch (e) {
                container.innerHTML = '<p style="color: #FF0000;">Lỗi tải lịch sử folder kết quả: ' + e.message + '</p>';
            }
        }

        // Initialize Firebase Listeners on load
        window.addEventListener('DOMContentLoaded', () => {
            if (LOCAL_CONFIG.firebase) {
                window.initLocalFirebaseSync(LOCAL_CONFIG.firebase);
            }
        });
    </script>
</body>
</html>
"""

class LocalAppHandler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200, "OK")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index", "/index.html"]:
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()

            cfg = load_local_config()

            html = HTML_TEMPLATE.replace("{ANHLOCAL_DIR}", cfg.get("anhlocal_dir", ""))
            html = html.replace("{OUTPUT_DIR}", cfg.get("output_dir", ""))
            
            custom = cfg.get("custom_nesting", {})
            html = html.replace("{CUSTOM_PAPER_SIZE}", str(custom.get("paper_size", "")))
            html = html.replace("{CUSTOM_WIDTH_MM}", str(custom.get("width_mm", 390.0)))
            html = html.replace("{CUSTOM_HEIGHT_MM}", str(custom.get("height_mm", 290.0)))
            html = html.replace("{CUSTOM_DPI}", str(custom.get("dpi", 500)))
            html = html.replace("{CUSTOM_PADDING_MM}", str(custom.get("padding_mm", 3.0)))

            pet = cfg.get("pet_nesting", {})
            html = html.replace("{PET_PAPER_SIZE}", str(pet.get("paper_size", "")))
            html = html.replace("{PET_WIDTH_MM}", str(pet.get("width_mm", 580.0)))
            html = html.replace("{PET_HEIGHT_MM}", str(pet.get("height_mm", 1000.0)))
            html = html.replace("{PET_DPI}", str(pet.get("dpi", 300)))
            html = html.replace("{PET_PADDING_MM}", str(pet.get("padding_mm", 5.0)))

            html = html.replace("{CONFIG_JSON_RAW}", json.dumps(cfg, ensure_ascii=False))

            self.wfile.write(html.encode("utf-8"))

        elif path == "/api/history":
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()

            cfg = load_local_config()
            output_dir = cfg.get("output_dir", "output")

            folders = []
            if os.path.exists(output_dir):
                for entry in sorted(os.listdir(output_dir), reverse=True):
                    full_p = os.path.join(output_dir, entry)
                    if os.path.isdir(full_p):
                        files = os.listdir(full_p)
                        pngs = [f for f in files if f.lower().endswith(".png")]
                        folders.append({
                            "name": entry,
                            "path": full_p,
                            "file_count": len(files),
                            "png_count": len(pngs)
                        })

            self.wfile.write(json.dumps(folders, ensure_ascii=False).encode("utf-8"))
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/process_job":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            
            try:
                job_data = json.loads(body)
                print(f"[API] Processing Job request: {job_data.get('id')}")
                result = safe_run_job_execution(job_data)
                
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                err_msg = f"API process_job error: {e}\n{traceback.format_exc()}"
                print(err_msg)
                self.send_response(500)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False).encode("utf-8"))

        elif path == "/api/save_config":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")

            try:
                new_cfg = json.loads(body)
                success = save_local_config(new_cfg)
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": success}, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

PROCESSED_JOBS_SET = set()

def parse_firestore_doc(doc_data):
    """Parses a Firestore REST document into a clean Python dictionary"""
    doc_name = doc_data.get("name", "")
    doc_id = doc_name.split("/")[-1] if doc_name else ""
    fields = doc_data.get("fields", {})
    
    result = {"id": doc_id}
    for k, v in fields.items():
        if "stringValue" in v:
            result[k] = v["stringValue"]
        elif "integerValue" in v:
            result[k] = int(v["integerValue"])
        elif "doubleValue" in v:
            result[k] = float(v["doubleValue"])
        elif "booleanValue" in v:
            result[k] = v["booleanValue"]
        elif "arrayValue" in v:
            arr_vals = v["arrayValue"].get("values", [])
            result[k] = [x.get("stringValue", "") for x in arr_vals if "stringValue" in x]
    return result

def patch_firestore_doc(collection_path, doc_id, fields_dict):
    """Updates fields of a document in Firestore via REST API"""
    try:
        project_id = "order-web-hoang"
        url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/{collection_path}/{doc_id}"
        
        update_masks = [f"updateMask.fieldPaths={k}" for k in fields_dict.keys()]
        full_url = f"{url}?{'&'.join(update_masks)}"
        
        fs_fields = {}
        for k, v in fields_dict.items():
            if isinstance(v, bool):
                fs_fields[k] = {"booleanValue": v}
            elif isinstance(v, int):
                fs_fields[k] = {"integerValue": str(v)}
            elif isinstance(v, float):
                fs_fields[k] = {"doubleValue": v}
            elif isinstance(v, list):
                fs_fields[k] = {"arrayValue": {"values": [{"stringValue": str(x)} for x in v]}}
            else:
                fs_fields[k] = {"stringValue": str(v)}
                
        body = json.dumps({"fields": fs_fields}).encode("utf-8")
        req = urllib.request.Request(full_url, data=body, headers={"Content-Type": "application/json"}, method="PATCH")
        with urllib.request.urlopen(req) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"[Python Backend] Firestore Patch Error for {doc_id}: {e}", flush=True)
        return False

JOB_LOCK = threading.Lock()
ACTIVE_PROCESSING_JOBS = set()
COMPLETED_JOB_RESULTS = {}

def safe_run_job_execution(job_data):
    """
    Thread-safe job execution manager:
    Prevents duplicate parallel execution of the same Print Job ID across multiple HTTP/Firebase threads.
    """
    job_id = job_data.get("id") or f"JOB-{int(time.time())}"
    
    with JOB_LOCK:
        if job_id in COMPLETED_JOB_RESULTS:
            print(f"ℹ️ [Job Manager] Job '{job_id}' đã hoàn thành trước đó. Trả về kết quả từ Cache.", flush=True)
            return COMPLETED_JOB_RESULTS[job_id]
            
        if job_id in ACTIVE_PROCESSING_JOBS:
            print(f"⚠️ [Job Manager] Job '{job_id}' đang được xử lý ở thread khác. Chờ hoàn tất...", flush=True)
            
    # Wait for active job if another thread is currently processing it
    while True:
        time.sleep(0.5)
        with JOB_LOCK:
            if job_id in COMPLETED_JOB_RESULTS:
                return COMPLETED_JOB_RESULTS[job_id]
            if job_id not in ACTIVE_PROCESSING_JOBS:
                ACTIVE_PROCESSING_JOBS.add(job_id)
                break

    try:
        result = run_job_execution(job_data)
        with JOB_LOCK:
            COMPLETED_JOB_RESULTS[job_id] = result
        return result
    finally:
        with JOB_LOCK:
            ACTIVE_PROCESSING_JOBS.discard(job_id)

def start_backend_firebase_listener():
    """
    Background daemon thread that continuously listens to Firebase Firestore 'print_jobs'
    directly from Python backend (100% independent of whether the browser frontend is open or closed).
    """
    def listener_loop():
        print("🟢 [Python Backend] 100% Standalone Firebase Firestore Listener Thread Active!", flush=True)
        project_id = "order-web-hoang"
        url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/print_jobs"

        while True:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "NestingBackend/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    docs = data.get("documents", [])
                    for doc_raw in docs:
                        job_data = parse_firestore_doc(doc_raw)
                        job_id = job_data.get("id")
                        status = job_data.get("status")

                        if status == "pending" and job_id not in PROCESSED_JOBS_SET:
                            PROCESSED_JOBS_SET.add(job_id)
                            print(f"\n⚡ [Python Backend Realtime] Nhận Print Job mới từ Firebase: {job_id} (Đơn: {job_data.get('order_id')})", flush=True)
                            
                            # Execute job safely in Python backend
                            result = safe_run_job_execution(job_data)
                            
                            # Update Firestore print_jobs status to 'completed'
                            patch_firestore_doc("print_jobs", job_id, {
                                "status": "completed",
                                "output_folder": result.get("relative_folder", ""),
                                "updatedAt": datetime.datetime.now().isoformat()
                            })
                            
                            # Update Firestore order document in MACCHOVUI to 'completed'
                            order_id = job_data.get("order_id")
                            if order_id:
                                order_ids = str(order_id).split(",")
                                for oid in order_ids:
                                    oid_clean = oid.strip()
                                    if oid_clean:
                                        patch_firestore_doc("MACCHOVUI", oid_clean, {
                                            "pod_print_status": "completed",
                                            "pod_print_status_text": "Đã hoàn thành in",
                                            "fulfillment_status_text": "Hoàn thành in",
                                            "sku_processed": True,
                                            "updatedAt": datetime.datetime.now().isoformat()
                                        })
                                        print(f"✅ [Python Backend] Cập nhật Trạng Thái POD đơn '{oid_clean}' sang 'Đã hoàn thành in' trên Firebase Firestore!", flush=True)

            except Exception:
                pass
            
            time.sleep(2)

    t = threading.Thread(target=listener_loop, daemon=True)
    t.start()

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

def start_server():
    import sys
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    from src.job_runner import get_valid_path
    cfg = load_local_config()
    out_dir = get_valid_path(cfg.get("output_dir"), "output")
    img_dir = get_valid_path(cfg.get("anhlocal_dir"), "ANHLOCAL")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(img_dir, exist_ok=True)

    # Start standalone Python backend Firebase listener thread
    start_backend_firebase_listener()

    httpd = ThreadingHTTPServer(("", PORT), LocalAppHandler)
    print(f"🌐 Local WebApp (Red Broadcast Design) đang chạy tại: http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nĐang dừng Local WebApp...")

if __name__ == "__main__":
    start_server()
