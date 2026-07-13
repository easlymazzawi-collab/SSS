/**
 * Admin userbot section — real multi-step login flow.
 * OTP never displayed back; phone masked; no secret in DOM.
 * All data via textContent — no innerHTML with user/server data.
 */

import api from '../api/client.js';
import { toast } from '../components/toast.js';

let _step = 'config'; // config | pending_code | pending_2fa | logged_in

export function renderTelegram(container) {
  container.innerHTML = '';
  const content = document.createElement('div');
  content.className = 'page-content';
  content.innerHTML = `
    <h2 style="font-size:18px;font-weight:700;margin-bottom:20px">Admin Userbot</h2>

    <!-- Config card -->
    <div class="card" id="ubConfigCard">
      <div class="card-header"><span class="card-title">Cấu hình API</span></div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">API ID</label>
            <input class="form-control" id="ubApiId" type="number" placeholder="1234567" autocomplete="off">
          </div>
          <div class="form-group">
            <label class="form-label">API Hash (32 ký tự)</label>
            <input class="form-control" id="ubApiHash" type="password" placeholder="••••••••••••••••••••••••••••••••" maxlength="32" autocomplete="new-password">
          </div>
        </div>
        <button class="btn btn-primary" id="ubSaveConfigBtn">Lưu cấu hình</button>
      </div>
    </div>

    <!-- Status card -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">Trạng thái userbot</span>
        <button class="btn btn-secondary btn-sm" id="ubRefreshBtn">↻ Làm mới</button>
      </div>
      <div class="card-body" id="ubStatus">
        <span class="spinner"></span>
      </div>
    </div>

    <!-- Login flow -->
    <div class="card" id="ubLoginCard">
      <div class="card-header"><span class="card-title">Đăng nhập</span></div>
      <div class="card-body">
        <!-- Step: phone -->
        <div id="stepPhone">
          <div class="form-group">
            <label class="form-label">Số điện thoại</label>
            <input class="form-control" id="ubPhone" type="tel" placeholder="+66812345678" autocomplete="tel">
          </div>
          <button class="btn btn-primary" id="ubSendCodeBtn">Gửi mã OTP</button>
        </div>

        <!-- Step: code -->
        <div id="stepCode" style="display:none">
          <div class="form-group">
            <label class="form-label">Mã OTP (nhận từ Telegram)</label>
            <input class="form-control" id="ubCode" type="text" placeholder="12345" maxlength="8" autocomplete="one-time-code">
          </div>
          <div style="display:flex;gap:8px">
            <button class="btn btn-secondary" id="ubBackToPhoneBtn">← Quay lại</button>
            <button class="btn btn-primary" id="ubConfirmCodeBtn">Xác nhận</button>
          </div>
        </div>

        <!-- Step: 2FA -->
        <div id="step2FA" style="display:none">
          <div class="form-group">
            <label class="form-label">Mật khẩu 2FA</label>
            <input class="form-control" id="ub2FAPass" type="password" placeholder="••••••••" autocomplete="current-password">
          </div>
          <button class="btn btn-primary" id="ubConfirm2FABtn">Đăng nhập</button>
        </div>

        <!-- Logged in -->
        <div id="stepLoggedIn" style="display:none">
          <div class="tag tag-green" style="margin-bottom:12px">✓ Đã kết nối</div>
          <div style="display:flex;gap:8px">
            <button class="btn btn-danger btn-sm" id="ubLogoutBtn">Đăng xuất</button>
            <button class="btn btn-secondary btn-sm" id="ubReloginBtn">Đổi tài khoản</button>
          </div>
        </div>
      </div>
    </div>
  `;
  container.appendChild(content);

  // Save config
  content.querySelector('#ubSaveConfigBtn').addEventListener('click', async () => {
    const apiId = parseInt(content.querySelector('#ubApiId').value);
    const apiHash = content.querySelector('#ubApiHash').value.trim();
    if (!apiId || !apiHash || apiHash.length !== 32) {
      toast.error('API ID và API Hash 32 ký tự là bắt buộc');
      return;
    }
    const btn = content.querySelector('#ubSaveConfigBtn');
    btn.disabled = true;
    const r = await api.telegram.saveConfig({ api_id: apiId, api_hash: apiHash, phone: '+66000000000' });
    btn.disabled = false;
    if (r.ok) {
      toast.success('Đã lưu cấu hình API');
      content.querySelector('#ubApiHash').value = '';
    } else {
      toast.error('Lỗi: ' + r.error);
    }
  });

  content.querySelector('#ubRefreshBtn').addEventListener('click', () => loadStatus(content));

  // Login flow
  content.querySelector('#ubSendCodeBtn').addEventListener('click', () => sendCode(content));
  content.querySelector('#ubBackToPhoneBtn').addEventListener('click', () => showStep(content, 'phone'));
  content.querySelector('#ubConfirmCodeBtn').addEventListener('click', () => confirmCode(content));
  content.querySelector('#ubConfirm2FABtn').addEventListener('click', () => confirm2FA(content));
  content.querySelector('#ubLogoutBtn').addEventListener('click', () => logoutUserbot(content));
  content.querySelector('#ubReloginBtn').addEventListener('click', () => {
    showStep(content, 'phone');
  });

  loadStatus(content);
}

async function loadStatus(content) {
  const el = content.querySelector('#ubStatus');
  const res = await api.telegram.userbotStatus();
  if (!res.ok) {
    el.textContent = 'Lỗi: ' + res.error;
    return;
  }
  const s = res.data;

  const statusMap = {
    connected: 'tag-green',
    pending_code: 'tag-amber',
    pending_2fa: 'tag-amber',
    disconnected: 'tag-muted',
    error: 'tag-red',
  };

  const statusEl = document.createElement('div');
  const tag = document.createElement('span');
  tag.className = `tag ${statusMap[s.status] || 'tag-muted'}`;
  tag.textContent = s.status;
  statusEl.appendChild(tag);

  if (s.username) {
    const name = document.createElement('span');
    name.style.cssText = 'margin-left:8px;color:var(--text)';
    name.textContent = '@' + s.username;
    statusEl.appendChild(name);
  }
  if (s.phone_masked) {
    const phone = document.createElement('span');
    phone.style.cssText = 'margin-left:8px;color:var(--muted);font-size:12px';
    phone.textContent = s.phone_masked;
    statusEl.appendChild(phone);
  }
  if (s.error_msg) {
    const err = document.createElement('div');
    err.style.cssText = 'color:var(--red);font-size:12px;margin-top:4px';
    err.textContent = s.error_msg;
    statusEl.appendChild(err);
  }

  el.innerHTML = '';
  el.appendChild(statusEl);

  // Update login flow step based on status
  if (s.status === 'connected') {
    showStep(content, 'logged_in');
  } else if (s.status === 'pending_code') {
    showStep(content, 'code');
  } else if (s.status === 'pending_2fa') {
    showStep(content, '2fa');
  } else {
    showStep(content, 'phone');
  }
}

function showStep(content, step) {
  content.querySelector('#stepPhone').style.display = step === 'phone' ? '' : 'none';
  content.querySelector('#stepCode').style.display = step === 'code' ? '' : 'none';
  content.querySelector('#step2FA').style.display = step === '2fa' ? '' : 'none';
  content.querySelector('#stepLoggedIn').style.display = step === 'logged_in' ? '' : 'none';
}

async function sendCode(content) {
  const phone = content.querySelector('#ubPhone').value.trim();
  if (!phone.match(/^\+\d{7,15}$/)) {
    toast.error('Số điện thoại không hợp lệ (vd: +66812345678)');
    return;
  }
  const btn = content.querySelector('#ubSendCodeBtn');
  btn.disabled = true;
  btn.textContent = '...';
  const r = await api.telegram.sendCode(phone);
  btn.disabled = false;
  btn.textContent = 'Gửi mã OTP';
  if (r.ok) {
    toast.success('Đã gửi mã OTP');
    showStep(content, 'code');
  } else {
    toast.error('Lỗi: ' + r.error);
  }
}

let _phone = '';
async function confirmCode(content) {
  const phone = content.querySelector('#ubPhone').value.trim();
  const code = content.querySelector('#ubCode').value.trim();
  if (!code) { toast.error('Nhập mã OTP'); return; }

  const btn = content.querySelector('#ubConfirmCodeBtn');
  btn.disabled = true;
  btn.textContent = '...';

  const r = await api.telegram.confirmCode({ phone, code, phone_code_hash: '' });
  btn.disabled = false;
  btn.textContent = 'Xác nhận';

  if (r.ok) {
    if (r.data.need_2fa) {
      showStep(content, '2fa');
      toast.info('Cần mật khẩu 2FA');
    } else {
      toast.success('Đã đăng nhập!');
      loadStatus(content);
    }
  } else {
    toast.error('Lỗi: ' + r.error);
  }
}

async function confirm2FA(content) {
  const password = content.querySelector('#ub2FAPass').value;
  if (!password) { toast.error('Nhập mật khẩu 2FA'); return; }
  const btn = content.querySelector('#ubConfirm2FABtn');
  btn.disabled = true;
  btn.textContent = '...';
  const r = await api.telegram.confirm2FA(password);
  content.querySelector('#ub2FAPass').value = '';
  btn.disabled = false;
  btn.textContent = 'Đăng nhập';
  if (r.ok) {
    toast.success('Đã đăng nhập!');
    loadStatus(content);
  } else {
    toast.error('Lỗi: ' + r.error);
  }
}

async function logoutUserbot(content) {
  const btn = content.querySelector('#ubLogoutBtn');
  btn.disabled = true;
  const r = await api.telegram.logout();
  btn.disabled = false;
  if (r.ok) {
    toast.success('Đã đăng xuất');
    loadStatus(content);
  } else {
    toast.error('Lỗi: ' + r.error);
  }
}
