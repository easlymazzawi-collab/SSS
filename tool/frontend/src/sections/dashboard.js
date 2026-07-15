/**
 * Dashboard section — shows real health status, no mock states.
 * Health data always from /api/health; never seeds "Ready"/"Armed" without backend response.
 */

import api from '../api/client.js';
import store from '../state/store.js';
import { toast } from '../components/toast.js';

export function renderDashboard(container) {
  container.innerHTML = '';

  const content = document.createElement('div');
  content.className = 'page-content';
  content.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
      <h2 style="font-size:18px;font-weight:700">Dashboard</h2>
      <button class="btn btn-secondary btn-sm" id="dashRefreshBtn">↻ Làm mới</button>
    </div>

    <div class="stats-grid" id="dashStats">
      <div class="stat-card"><div class="stat-label">Backend</div><div class="stat-value" id="dBackend">—</div></div>
      <div class="stat-card"><div class="stat-label">Database</div><div class="stat-value" id="dDb">—</div></div>
      <div class="stat-card"><div class="stat-label">Worker</div><div class="stat-value" id="dWorker">—</div></div>
      <div class="stat-card"><div class="stat-label">Telegram</div><div class="stat-value" id="dTg">—</div></div>
    </div>

    <div class="card">
      <div class="card-header"><span class="card-title">Hệ thống</span></div>
      <div class="card-body" id="machineInfo">
        <span class="spinner"></span> Đang tải...
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">Jobs đang chạy</span>
        <button class="btn btn-secondary btn-sm" id="dashJobsRefresh">↻</button>
      </div>
      <div class="card-body" id="activeJobsList">
        <span class="spinner"></span>
      </div>
    </div>
  `;

  container.appendChild(content);

  const refreshBtn = content.querySelector('#dashRefreshBtn');
  const jobsRefresh = content.querySelector('#dashJobsRefresh');

  refreshBtn.addEventListener('click', () => loadHealth(content));
  jobsRefresh.addEventListener('click', () => loadJobs(content));

  loadHealth(content);
  loadJobs(content);
}

async function loadHealth(content) {
  const res = await api.health();
  if (!res.ok) {
    content.querySelector('#dBackend').textContent = 'ERROR';
    content.querySelector('#dBackend').style.color = 'var(--red)';
    toast.error('Không kết nối được backend: ' + res.error);
    return;
  }

  const h = res.data;
  store.set('health', h);

  const setStatus = (id, val, good = true) => {
    const el = content.querySelector(`#${id}`);
    if (el) {
      el.textContent = val;
      el.style.color = good ? 'var(--green)' : 'var(--red)';
    }
  };

  setStatus('dBackend', h.backend_alive ? 'OK' : 'ERROR', h.backend_alive);
  setStatus('dDb', h.db_ready ? 'OK' : 'ERROR', h.db_ready);
  setStatus('dWorker', h.worker_ready ? 'Running' : 'Stopped', h.worker_ready);
  setStatus('dTg', h.telegram_connected ? (h.telegram_username || 'Connected') : 'Offline', h.telegram_connected);

  const machine = content.querySelector('#machineInfo');
  if (machine && h.machine) {
    const m = h.machine;
    machine.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px">
        <div><div class="stat-label">CPU</div><div style="font-size:18px;font-weight:700">${m.cpu_pct ?? '—'}%</div></div>
        <div><div class="stat-label">RAM</div><div style="font-size:18px;font-weight:700">${m.ram_used_mb ?? '—'} MB</div><div class="stat-sub">/ ${m.ram_total_mb ?? '—'} MB</div></div>
        <div><div class="stat-label">Disk</div><div style="font-size:18px;font-weight:700">${m.disk_used_gb ?? '—'} GB</div><div class="stat-sub">/ ${m.disk_total_gb ?? '—'} GB</div></div>
        <div><div class="stat-label">Uptime</div><div style="font-size:18px;font-weight:700">${formatUptime(h.uptime_seconds)}</div></div>
        <div><div class="stat-label">Python</div><div style="font-size:14px;font-weight:600">${h.python_version ?? '—'}</div></div>
      </div>
    `;
  }
}

async function loadJobs(content) {
  const el = content.querySelector('#activeJobsList');
  if (!el) return;

  const res = await api.runtime.jobs(20);
  if (!res.ok) {
    el.textContent = 'Lỗi tải jobs: ' + res.error;
    return;
  }

  const active = res.data.filter(j => ['queued', 'running', 'waiting_flood'].includes(j.status));
  if (active.length === 0) {
    el.innerHTML = '<div class="empty"><div class="empty-icon">✓</div><h3>Không có job nào đang chạy</h3></div>';
    return;
  }

  el.innerHTML = `
    <table>
      <thead><tr><th>ID</th><th>Loại</th><th>Trạng thái</th><th>Tiến độ</th><th></th></tr></thead>
      <tbody>
        ${active.map(j => `
          <tr>
            <td>#${j.id}</td>
            <td><code>${escText(j.job_type)}</code></td>
            <td><span class="tag job-${j.status}">${escText(j.status)}</span></td>
            <td>
              <div class="progress-bar" style="width:120px">
                <div class="progress-fill" style="width:${j.progress?.pct ?? 0}%"></div>
              </div>
              <small>${j.progress?.done ?? 0}/${j.progress?.total ?? '?'}</small>
            </td>
            <td>
              <button class="btn btn-danger btn-sm" data-cancel-job="${j.id}">✕ Hủy</button>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;

  el.querySelectorAll('[data-cancel-job]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const jobId = parseInt(btn.dataset.cancelJob);
      btn.disabled = true;
      const r = await api.runtime.cancelJob(jobId);
      if (r.ok) {
        toast.success('Đã hủy job #' + jobId);
        loadJobs(content);
      } else {
        toast.error('Lỗi hủy job: ' + r.error);
        btn.disabled = false;
      }
    });
  });
}

function formatUptime(seconds) {
  if (!seconds) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function escText(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
