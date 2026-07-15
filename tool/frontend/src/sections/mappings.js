/**
 * Topic mappings section — full CRUD with real backend.
 * Destinations are saved to DB; no partial-save false success.
 */

import api from '../api/client.js';
import { toast } from '../components/toast.js';
import { confirm } from '../components/modal.js';
import { JobSSE } from '../api/sse.js';

let _mappings = [];
let _activeSSE = null;

export function renderMappings(container) {
  container.innerHTML = '';
  const content = document.createElement('div');
  content.className = 'page-content';
  content.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
      <h2 style="font-size:18px;font-weight:700">Up bài ads</h2>
      <div style="display:flex;gap:8px">
        <button class="btn btn-secondary btn-sm" id="genMapBtn">⬇ Sinh topic_map.txt</button>
        <button class="btn btn-primary btn-sm" id="addMappingBtn">+ Thêm mapping</button>
      </div>
    </div>

    <!-- Add/Edit form -->
    <div class="card" id="mappingFormCard" style="display:none">
      <div class="card-header">
        <span class="card-title" id="mappingFormTitle">Thêm mapping</span>
        <button class="btn btn-ghost btn-sm" id="cancelMappingBtn">✕</button>
      </div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Tên mapping *</label>
            <input class="form-control" id="mappingName" placeholder="vd: vitamin → pro">
          </div>
          <div class="form-group">
            <label class="form-label">Nguồn Chat ID *</label>
            <input class="form-control" id="mappingSrcChat" type="number" placeholder="-1001234567890">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Topic ID nguồn (để trống nếu không dùng topic)</label>
            <input class="form-control" id="mappingSrcTopic" type="number" placeholder="0">
          </div>
          <div class="form-group">
            <label class="form-label">Chế độ ads</label>
            <select class="form-control" id="mappingAdsMode">
              <option value="normal">Normal (xen đều)</option>
              <option value="xdone">XDone (ads giữa)</option>
              <option value="zdone">ZDone (ads trước)</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Đích (Destinations)</label>
          <div id="destStack"></div>
          <button class="btn btn-secondary btn-sm" id="addDestBtn" style="margin-top:8px">+ Thêm đích</button>
        </div>

        <div style="display:flex;gap:8px;justify-content:flex-end">
          <button class="btn btn-secondary" id="cancelMappingBtn2">Hủy</button>
          <button class="btn btn-primary" id="saveMappingBtn">Lưu mapping</button>
        </div>
      </div>
    </div>

    <!-- List -->
    <div id="mappingList"></div>
  `;
  container.appendChild(content);

  let editingId = null;

  content.querySelector('#addMappingBtn').addEventListener('click', () => {
    editingId = null;
    showForm(content, null);
  });
  content.querySelectorAll('#cancelMappingBtn, #cancelMappingBtn2').forEach(btn => {
    btn.addEventListener('click', () => hideForm(content));
  });
  content.querySelector('#addDestBtn').addEventListener('click', () => addDestRow(content));
  content.querySelector('#saveMappingBtn').addEventListener('click', () => saveMapping(content, editingId));
  content.querySelector('#genMapBtn').addEventListener('click', () => generateTopicMap());

  loadMappings(content);
}

async function loadMappings(content) {
  const el = content.querySelector('#mappingList');
  el.innerHTML = '<span class="spinner"></span>';
  const res = await api.mappings.list();
  if (!res.ok) {
    el.innerHTML = `<div class="empty"><h3>Lỗi: ${escText(res.error)}</h3></div>`;
    return;
  }
  _mappings = res.data;
  renderMappingList(el, content);
}

function renderMappingList(el, content) {
  if (_mappings.length === 0) {
    el.innerHTML = '<div class="empty"><div class="empty-icon">🗺</div><h3>Chưa có mapping nào</h3></div>';
    return;
  }
  el.innerHTML = _mappings.map(m => `
    <div class="card" style="margin-bottom:12px">
      <div class="card-header">
        <div>
          <span class="card-title">${escText(m.name)}</span>
          <span class="tag ${m.is_active ? 'tag-green' : 'tag-muted'}" style="margin-left:8px">${m.is_active ? 'Active' : 'Inactive'}</span>
          <span class="tag tag-blue" style="margin-left:4px">${escText(m.ads_mode)}</span>
        </div>
        <div style="display:flex;gap:6px">
          <button class="btn btn-green btn-sm" data-run-mapping="${m.id}">▶ Run</button>
          <button class="btn btn-secondary btn-sm" data-edit-mapping="${m.id}">✎ Sửa</button>
          <button class="btn btn-danger btn-sm" data-del-mapping="${m.id}">✕</button>
        </div>
      </div>
      <div class="card-body" style="font-size:13px">
        <div style="color:var(--muted);margin-bottom:8px">
          Nguồn: <code>${m.source_chat_id}</code>
          ${m.source_topic_id ? ` → Topic <code>${m.source_topic_id}</code>` : ''}
        </div>
        <div style="color:var(--muted);font-size:12px">
          ${m.destinations.length} đích: ${m.destinations.map(d => `<code>${d.dest_chat_id}${d.dest_topic_id ? '/' + d.dest_topic_id : ''}</code>`).join(', ')}
        </div>
        <div id="job-progress-${m.id}" style="display:none;margin-top:8px">
          <div class="progress-bar"><div class="progress-fill" id="prog-fill-${m.id}" style="width:0%"></div></div>
          <small id="prog-text-${m.id}" style="color:var(--muted)">0/0</small>
        </div>
      </div>
    </div>
  `).join('');

  el.querySelectorAll('[data-run-mapping]').forEach(btn => {
    btn.addEventListener('click', () => runMapping(parseInt(btn.dataset.runMapping), content, el));
  });
  el.querySelectorAll('[data-edit-mapping]').forEach(btn => {
    btn.addEventListener('click', () => {
      const m = _mappings.find(x => x.id === parseInt(btn.dataset.editMapping));
      if (m) showForm(content, m);
    });
  });
  el.querySelectorAll('[data-del-mapping]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.dataset.delMapping);
      const ok = await confirm('Xóa mapping này?', { danger: true, confirmLabel: 'Xóa' });
      if (!ok) return;
      btn.disabled = true;
      const r = await api.mappings.delete(id);
      if (r.ok) {
        toast.success('Đã xóa mapping');
        loadMappings(content);
      } else {
        toast.error('Lỗi: ' + r.error);
        btn.disabled = false;
      }
    });
  });
}

async function runMapping(mappingId, content, listEl) {
  const ok = await confirm(
    'Chạy mapping này? Sẽ forward tin nhắn từ nguồn đến các đích.',
    { title: 'Chạy mapping', confirmLabel: 'Chạy' }
  );
  if (!ok) return;

  const res = await api.runtime.runMapping({
    mapping_id: mappingId,
    dry_run: false,
    send_cap: 500,
  });
  if (!res.ok) {
    toast.error('Lỗi khởi chạy: ' + res.error);
    return;
  }

  const job = res.data;
  toast.success(`Job #${job.id} đã tạo, đang chạy...`);

  // Show progress
  const progEl = listEl.querySelector(`#job-progress-${mappingId}`);
  if (progEl) progEl.style.display = 'block';

  if (_activeSSE) _activeSSE.close();
  _activeSSE = new JobSSE(job.id, (event) => {
    if (event.type === 'progress') {
      const fill = listEl.querySelector(`#prog-fill-${mappingId}`);
      const text = listEl.querySelector(`#prog-text-${mappingId}`);
      if (fill) fill.style.width = `${event.pct}%`;
      if (text) text.textContent = `${event.done}/${event.total} (${event.pct}%)`;
    } else if (event.type === 'finished' || event.type === 'failed' || event.type === 'cancelled') {
      _activeSSE?.close();
      toast.info(`Job #${job.id} ${event.type}`);
    }
  });
}

function showForm(content, mapping) {
  const card = content.querySelector('#mappingFormCard');
  card.style.display = 'block';
  card.querySelector('#mappingFormTitle').textContent = mapping ? 'Sửa mapping' : 'Thêm mapping';
  content.querySelector('#mappingName').value = mapping?.name || '';
  content.querySelector('#mappingSrcChat').value = mapping?.source_chat_id || '';
  content.querySelector('#mappingSrcTopic').value = mapping?.source_topic_id || '';
  content.querySelector('#mappingAdsMode').value = mapping?.ads_mode || 'normal';

  const stack = content.querySelector('#destStack');
  stack.innerHTML = '';
  if (mapping?.destinations?.length) {
    mapping.destinations.forEach(d => addDestRow(content, d));
  } else {
    addDestRow(content);
  }
  card.scrollIntoView({ behavior: 'smooth' });
}

function hideForm(content) {
  content.querySelector('#mappingFormCard').style.display = 'none';
}

function addDestRow(content, dest = null) {
  const stack = content.querySelector('#destStack');
  const row = document.createElement('div');
  row.className = 'form-row';
  row.style.cssText = 'align-items:center;margin-bottom:8px';
  row.innerHTML = `
    <input class="form-control dest-chat-id" type="number" placeholder="Dest Chat ID" value="${dest?.dest_chat_id || ''}">
    <input class="form-control dest-topic-id" type="number" placeholder="Topic ID (tùy chọn)" value="${dest?.dest_topic_id || ''}">
    <button class="btn btn-ghost btn-sm" style="flex-shrink:0" data-remove-dest>✕</button>
  `;
  row.querySelector('[data-remove-dest]').addEventListener('click', () => {
    if (stack.children.length > 1) {
      row.remove();
    } else {
      row.querySelector('.dest-chat-id').value = '';
      row.querySelector('.dest-topic-id').value = '';
    }
  });
  stack.appendChild(row);
}

async function saveMapping(content, editingId) {
  const name = content.querySelector('#mappingName').value.trim();
  const srcChat = parseInt(content.querySelector('#mappingSrcChat').value);
  const srcTopic = parseInt(content.querySelector('#mappingSrcTopic').value) || null;
  const adsMode = content.querySelector('#mappingAdsMode').value;

  if (!name) { toast.error('Cần nhập tên mapping'); return; }
  if (!srcChat) { toast.error('Cần nhập Chat ID nguồn'); return; }

  const destinations = [];
  content.querySelectorAll('#destStack .form-row').forEach(row => {
    const chatId = parseInt(row.querySelector('.dest-chat-id').value);
    const topicId = parseInt(row.querySelector('.dest-topic-id').value) || null;
    if (chatId) destinations.push({ dest_chat_id: chatId, dest_topic_id: topicId });
  });

  const saveBtn = content.querySelector('#saveMappingBtn');
  saveBtn.disabled = true;
  saveBtn.textContent = '...';

  const body = { name, source_chat_id: srcChat, source_topic_id: srcTopic, ads_mode: adsMode, destinations };

  let res;
  if (editingId) {
    res = await api.mappings.update(editingId, body);
  } else {
    res = await api.mappings.create(body);
  }

  saveBtn.disabled = false;
  saveBtn.textContent = 'Lưu mapping';

  if (res.ok) {
    toast.success(editingId ? 'Đã cập nhật mapping' : 'Đã thêm mapping');
    hideForm(content);
    loadMappings(content);
  } else {
    toast.error('Lỗi: ' + res.error);
  }
}

function generateTopicMap() {
  const lines = _mappings
    .filter(m => m.is_active)
    .map(m => `# ${m.name}\n${m.source_chat_id} → ${m.destinations.map(d => d.dest_chat_id).join(', ')}`);
  const blob = new Blob([lines.join('\n\n')], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'topic_map.txt';
  a.click();
  URL.revokeObjectURL(url);
}

function escText(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
