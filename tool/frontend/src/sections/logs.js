/**
 * Realtime logs section — SSE-backed with REST fallback.
 */

import { LogSSE } from '../api/sse.js';
import api from '../api/client.js';
import { toast } from '../components/toast.js';

let _sse = null;
let _entries = [];

export function renderLogs(container) {
  container.innerHTML = '';
  const content = document.createElement('div');
  content.className = 'page-content';
  content.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
      <h2 style="font-size:18px;font-weight:700">Log realtime</h2>
      <div style="display:flex;gap:8px;align-items:center">
        <span id="sseStatus" class="tag tag-muted">Connecting...</span>
        <button class="btn btn-secondary btn-sm" id="clearLogsBtn">✕ Xóa log</button>
      </div>
    </div>
    <div class="card">
      <div class="card-body" style="padding:0">
        <div class="log-container" id="logContainer"></div>
      </div>
    </div>
  `;
  container.appendChild(content);

  const logContainer = content.querySelector('#logContainer');
  const sseStatus = content.querySelector('#sseStatus');

  content.querySelector('#clearLogsBtn').addEventListener('click', () => {
    _entries = [];
    logContainer.innerHTML = '';
    toast.info('Đã xóa log UI');
  });

  // Start SSE
  if (_sse) _sse.close();
  _sse = new LogSSE((entry) => {
    sseStatus.textContent = 'Live';
    sseStatus.className = 'tag tag-green';
    addEntry(logContainer, entry);
  });

  // Error handler via polling fallback
  setTimeout(() => {
    if (sseStatus.textContent === 'Connecting...') {
      sseStatus.textContent = 'Polling';
      sseStatus.className = 'tag tag-amber';
    }
  }, 5000);
}

function addEntry(container, entry) {
  _entries.push(entry);
  if (_entries.length > 500) {
    _entries.shift();
    container.firstChild?.remove();
  }

  const el = document.createElement('div');
  el.className = `log-entry log-${entry.level || 'INFO'}`;
  const time = document.createElement('span');
  time.style.color = 'var(--muted)';
  time.textContent = (entry.ts || '').slice(11, 19) + ' ';
  const level = document.createElement('span');
  level.style.fontWeight = '700';
  level.textContent = `[${entry.level || 'INFO'}] `;
  const msg = document.createElement('span');
  msg.textContent = entry.msg || '';

  el.appendChild(time);
  el.appendChild(level);
  el.appendChild(msg);
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
}

export function destroyLogs() {
  if (_sse) {
    _sse.close();
    _sse = null;
  }
}
