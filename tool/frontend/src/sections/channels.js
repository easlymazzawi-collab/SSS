/**
 * Channel registry section — real CRUD with backend.
 * No optimistic updates without DB confirmation.
 */

import api from '../api/client.js';
import { toast } from '../components/toast.js';
import { confirm, createModal } from '../components/modal.js';

let _channels = [];

export function renderChannels(container) {
  container.innerHTML = '';
  const content = document.createElement('div');
  content.className = 'page-content';
  content.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
      <h2 style="font-size:18px;font-weight:700">Kênh & Folder</h2>
      <div style="display:flex;gap:8px">
        <button class="btn btn-secondary btn-sm" id="checkDeadBtn">🔍 Check kênh chết</button>
        <button class="btn btn-primary btn-sm" id="addChannelBtn">+ Thêm kênh</button>
      </div>
    </div>
    <div class="card">
      <div class="card-body" id="channelList"><span class="spinner"></span></div>
    </div>
  `;
  container.appendChild(content);

  content.querySelector('#addChannelBtn').addEventListener('click', () => showAddModal(content));
  content.querySelector('#checkDeadBtn').addEventListener('click', () => checkDead(content));

  loadChannels(content);
}

async function loadChannels(content) {
  const el = content.querySelector('#channelList');
  const res = await api.channels.list();
  if (!res.ok) {
    el.innerHTML = `<div class="empty"><div class="empty-icon">⚠</div><h3>Lỗi tải kênh: ${escText(res.error)}</h3></div>`;
    return;
  }
  _channels = res.data;
  renderList(el);
}

function renderList(el) {
  if (_channels.length === 0) {
    el.innerHTML = '<div class="empty"><div class="empty-icon">📡</div><h3>Chưa có kênh nào</h3><p>Bấm "+ Thêm kênh" để bắt đầu</p></div>';
    return;
  }
  el.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Chat ID</th><th>Tên</th><th>Username</th><th>Trạng thái</th><th>Forum</th><th></th></tr></thead>
        <tbody>
          ${_channels.map(ch => `
            <tr data-channel-id="${ch.id}">
              <td><code>${ch.chat_id}</code></td>
              <td>${escText(ch.title || '—')}</td>
              <td>${ch.username ? `@${escText(ch.username)}` : '—'}</td>
              <td>${livenessTag(ch.liveness)}</td>
              <td>${ch.is_forum ? '<span class="tag tag-blue">Forum</span>' : '—'}</td>
              <td style="white-space:nowrap">
                <button class="btn btn-ghost btn-sm" data-check-ch="${ch.id}" title="Kiểm tra liveness">🔍</button>
                <button class="btn btn-danger btn-sm" data-del-ch="${ch.id}" title="Xóa">✕</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;

  el.querySelectorAll('[data-check-ch]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.dataset.checkCh);
      btn.disabled = true;
      btn.textContent = '⏳';
      const r = await api.channels.checkLiveness(id);
      if (r.ok) {
        toast.success(`Kênh ${r.data.chat_id}: ${r.data.liveness}`);
        loadChannels(el.closest('.page-content'));
      } else {
        toast.error('Lỗi: ' + r.error);
        btn.disabled = false;
        btn.textContent = '🔍';
      }
    });
  });

  el.querySelectorAll('[data-del-ch]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.dataset.delCh);
      const ok = await confirm('Xóa kênh này khỏi registry?', { danger: true, confirmLabel: 'Xóa' });
      if (!ok) return;
      btn.disabled = true;
      const r = await api.channels.delete(id);
      if (r.ok) {
        toast.success('Đã xóa kênh');
        loadChannels(el.closest('.page-content'));
      } else {
        toast.error('Lỗi xóa: ' + r.error);
        btn.disabled = false;
      }
    });
  });
}

function showAddModal(content) {
  const form = document.createElement('div');
  form.innerHTML = `
    <div class="form-group">
      <label class="form-label">Chat ID (số âm cho channel/supergroup)</label>
      <input class="form-control" id="addChatId" type="number" placeholder="-1001234567890">
    </div>
    <div class="form-group">
      <label class="form-label">Username (tùy chọn)</label>
      <input class="form-control" id="addUsername" type="text" placeholder="channel_username">
    </div>
    <div class="form-group">
      <label class="form-label">Tên (tùy chọn)</label>
      <input class="form-control" id="addTitle" type="text" placeholder="Tên kênh">
    </div>
  `;

  const footer = document.createElement('div');
  footer.style.cssText = 'display:flex;gap:8px';

  const cancelBtn = document.createElement('button');
  cancelBtn.className = 'btn btn-secondary';
  cancelBtn.textContent = 'Hủy';

  const submitBtn = document.createElement('button');
  submitBtn.className = 'btn btn-primary';
  submitBtn.textContent = 'Thêm';

  footer.appendChild(cancelBtn);
  footer.appendChild(submitBtn);

  const { close } = createModal({ title: 'Thêm kênh', body: form, footer });

  cancelBtn.addEventListener('click', close);
  submitBtn.addEventListener('click', async () => {
    const chatId = parseInt(form.querySelector('#addChatId').value);
    if (!chatId || chatId === 0) {
      toast.error('Chat ID không hợp lệ');
      return;
    }
    submitBtn.disabled = true;
    submitBtn.textContent = '...';
    const r = await api.channels.add({
      chat_id: chatId,
      username: form.querySelector('#addUsername').value.replace('@', '') || null,
      title: form.querySelector('#addTitle').value || null,
    });
    if (r.ok) {
      toast.success('Đã thêm kênh');
      close();
      loadChannels(content);
    } else {
      toast.error('Lỗi: ' + r.error);
      submitBtn.disabled = false;
      submitBtn.textContent = 'Thêm';
    }
  });
}

async function checkDead(content) {
  const chatIds = _channels.map(c => c.chat_id);
  if (chatIds.length === 0) {
    toast.warning('Không có kênh nào để check');
    return;
  }
  const btn = content.querySelector('#checkDeadBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Đang check...';
  const r = await api.channels.checkDead(chatIds.slice(0, 50));
  btn.disabled = false;
  btn.textContent = '🔍 Check kênh chết';
  if (r.ok) {
    const dead = Object.entries(r.data).filter(([, v]) => v === 'dead').length;
    toast.info(`Check xong: ${dead} kênh chết / ${chatIds.length} tổng`);
    loadChannels(content);
  } else {
    toast.error('Lỗi: ' + r.error);
  }
}

function livenessTag(l) {
  const map = { alive: 'tag-green', dead: 'tag-red', no_access: 'tag-amber', unknown: 'tag-muted' };
  return `<span class="tag ${map[l] || 'tag-muted'}">${escText(l)}</span>`;
}

function escText(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
