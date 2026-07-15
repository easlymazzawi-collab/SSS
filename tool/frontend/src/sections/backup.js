/**
 * Backup & data section — real backup/restore with integrity check.
 */

import api from '../api/client.js';
import { toast } from '../components/toast.js';
import { confirm } from '../components/modal.js';

export function renderBackup(container) {
  container.innerHTML = '';
  const content = document.createElement('div');
  content.className = 'page-content';
  content.innerHTML = `
    <h2 style="font-size:18px;font-weight:700;margin-bottom:20px">Backup & Dữ liệu</h2>

    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><span class="card-title">Backup</span></div>
      <div class="card-body">
        <p style="color:var(--muted);margin-bottom:12px;font-size:13px">
          Backup tạo file zip từ DB và config. Session file bị loại trừ để bảo vệ tài khoản.
        </p>
        <button class="btn btn-primary" id="backupNowBtn">⬇ Backup ngay</button>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">Lịch sử backup</span>
        <button class="btn btn-secondary btn-sm" id="backupListRefresh">↻</button>
      </div>
      <div class="card-body" id="backupList"><span class="spinner"></span></div>
    </div>

    <div class="card" style="margin-top:16px">
      <div class="card-header"><span class="card-title">Restore</span></div>
      <div class="card-body">
        <p style="color:var(--amber);margin-bottom:12px;font-size:13px">
          ⚠ Restore sẽ ghi đè dữ liệu hiện tại. Session file trong zip sẽ bị bỏ qua.
        </p>
        <input type="file" id="restoreFile" accept=".zip" style="display:none">
        <button class="btn btn-secondary" id="restorePickBtn">Chọn file backup (.zip)</button>
        <button class="btn btn-danger" id="restoreConfirmBtn" style="display:none" disabled>Restore</button>
        <span id="restoreFilename" style="margin-left:8px;color:var(--muted);font-size:12px"></span>
      </div>
    </div>
  `;
  container.appendChild(content);

  content.querySelector('#backupNowBtn').addEventListener('click', () => runBackup(content));
  content.querySelector('#backupListRefresh').addEventListener('click', () => loadBackupList(content));

  const fileInput = content.querySelector('#restoreFile');
  content.querySelector('#restorePickBtn').addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) {
      content.querySelector('#restoreFilename').textContent = fileInput.files[0].name;
      const btn = content.querySelector('#restoreConfirmBtn');
      btn.style.display = '';
      btn.disabled = false;
    }
  });
  content.querySelector('#restoreConfirmBtn').addEventListener('click', () => restoreBackup(content, fileInput));

  loadBackupList(content);
}

async function runBackup(content) {
  const btn = content.querySelector('#backupNowBtn');
  btn.disabled = true;
  btn.textContent = '...';
  const r = await api.backup.runNow();
  btn.disabled = false;
  btn.textContent = '⬇ Backup ngay';
  if (r.ok) {
    toast.success('Backup thành công: ' + r.data.filename);
    loadBackupList(content);
  } else {
    toast.error('Lỗi backup: ' + r.error);
  }
}

async function loadBackupList(content) {
  const el = content.querySelector('#backupList');
  const r = await api.backup.list();
  if (!r.ok) {
    el.textContent = 'Lỗi: ' + r.error;
    return;
  }
  if (r.data.length === 0) {
    el.innerHTML = '<div class="empty"><div class="empty-icon">📦</div><h3>Chưa có backup nào</h3></div>';
    return;
  }
  el.innerHTML = `
    <table>
      <thead><tr><th>Filename</th><th>Size</th><th>SHA256</th><th>Thời gian</th><th></th></tr></thead>
      <tbody>
        ${r.data.map(b => `
          <tr>
            <td><code>${escText(b.filename)}</code></td>
            <td>${formatSize(b.size_bytes)}</td>
            <td><code style="font-size:11px">${escText(b.sha256_prefix || '—')}</code></td>
            <td style="color:var(--muted);font-size:12px">${new Date(b.created_at).toLocaleString('vi-VN')}</td>
            <td>
              <a class="btn btn-secondary btn-sm" href="${escText(api.backup.downloadUrl(b.filename))}" download>⬇</a>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

async function restoreBackup(content, fileInput) {
  if (!fileInput.files[0]) return;
  const ok = await confirm(
    'Restore sẽ ghi đè dữ liệu hiện tại. Tiếp tục?',
    { title: 'Xác nhận Restore', confirmLabel: 'Restore', danger: true }
  );
  if (!ok) return;

  const btn = content.querySelector('#restoreConfirmBtn');
  btn.disabled = true;
  btn.textContent = '...';

  const form = new FormData();
  form.append('file', fileInput.files[0]);

  try {
    const res = await fetch('/api/backup/restore', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRF-Token': getCsrf() },
      body: form,
    });
    const json = await res.json();
    if (json.ok) {
      toast.success('Restore thành công');
    } else {
      toast.error('Lỗi restore: ' + (json.error || json.detail));
    }
  } catch (e) {
    toast.error('Lỗi: ' + e.message);
  }

  btn.disabled = false;
  btn.textContent = 'Restore';
}

function getCsrf() {
  const m = document.cookie.match(/upbain_csrf=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}

function formatSize(bytes) {
  if (!bytes) return '—';
  if (bytes > 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  return (bytes / 1024).toFixed(0) + ' KB';
}

function escText(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
