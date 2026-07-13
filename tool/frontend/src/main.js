/**
 * UpBain Control — Main application entry point.
 *
 * Architecture:
 * - Auth check on load; redirect to login if not authenticated
 * - Single API client, single origin (/api/...)
 * - Tab routing via URL hash + store (preferences only in localStorage)
 * - All sections rendered on demand; business data always from API
 * - SSE for realtime logs and job progress
 * - No mock states, no false-success toasts
 */

import api from './api/client.js';
import store from './state/store.js';
import { toast } from './components/toast.js';
import { renderDashboard } from './sections/dashboard.js';
import { renderChannels } from './sections/channels.js';
import { renderMappings } from './sections/mappings.js';
import { renderTelegram } from './sections/telegram.js';
import { renderLogs, destroyLogs } from './sections/logs.js';
import { renderBackup } from './sections/backup.js';

// -----------------------------------------------------------------------
// Login page
// -----------------------------------------------------------------------

function showLogin() {
  document.getElementById('app').innerHTML = `
    <div class="login-page">
      <div class="login-box">
        <div class="login-logo">UpBain</div>
        <form id="loginForm" autocomplete="on" novalidate>
          <div class="form-group">
            <label class="form-label" for="loginUser">Tên đăng nhập</label>
            <input class="form-control" id="loginUser" name="username" type="text" required autocomplete="username">
          </div>
          <div class="form-group">
            <label class="form-label" for="loginPass">Mật khẩu</label>
            <input class="form-control" id="loginPass" name="password" type="password" required autocomplete="current-password">
          </div>
          <button class="btn btn-primary" style="width:100%" type="submit" id="loginBtn">Đăng nhập</button>
          <div class="login-error" id="loginError" aria-live="polite"></div>
        </form>
      </div>
    </div>
  `;

  document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('loginUser').value;
    const password = document.getElementById('loginPass').value;
    const btn = document.getElementById('loginBtn');
    const errEl = document.getElementById('loginError');

    btn.disabled = true;
    btn.textContent = '...';
    errEl.textContent = '';

    const res = await api.login(username, password);

    if (res.ok) {
      store.set('auth', { authenticated: true, username: res.data.username, role: res.data.role });
      showApp();
    } else {
      errEl.textContent = res.error || 'Đăng nhập thất bại';
      btn.disabled = false;
      btn.textContent = 'Đăng nhập';
    }
  });
}

// -----------------------------------------------------------------------
// Main app
// -----------------------------------------------------------------------

const TABS = [
  { id: 'dashboard', label: 'Điều khiển', icon: '⊞' },
  { id: 'topics', label: 'Up bài ads', icon: '🗺' },
  { id: 'channels', label: 'Kênh & folder', icon: '📡' },
  { id: 'telegram', label: 'Admin userbot', icon: '👤' },
  { id: 'import', label: 'Backup & dữ liệu', icon: '💾' },
  { id: 'logs', label: 'Log realtime', icon: '📋' },
];

function showApp() {
  const activeTab = store.get('prefs').activeTab || 'dashboard';
  document.getElementById('app').innerHTML = `
    <div class="layout">
      <aside class="sidebar" role="navigation" aria-label="Điều hướng chính">
        <div class="sidebar-logo">UpBain</div>
        <nav class="sidebar-nav">
          ${TABS.map(t => `
            <button class="nav-link ${t.id === activeTab ? 'active' : ''}"
                    data-tab="${t.id}"
                    aria-current="${t.id === activeTab ? 'page' : 'false'}">
              <span class="nav-icon" aria-hidden="true">${t.icon}</span>
              ${t.label}
            </button>
          `).join('')}
        </nav>
        <div style="padding:12px;border-top:1px solid var(--line)">
          <button class="btn btn-ghost btn-sm" id="logoutBtn" style="width:100%">⎋ Đăng xuất</button>
        </div>
      </aside>

      <div class="main">
        <header class="topbar" role="banner">
          <h1>UpBain Control</h1>
          <div class="topbar-spacer"></div>
          <span id="topbarHealth" class="status-badge warning">
            <span class="status-dot"></span> Checking...
          </span>
          <div style="display:flex;gap:8px;margin-left:8px">
            <button class="btn btn-green btn-sm" id="startBtn">▶ START</button>
            <button class="btn btn-danger btn-sm" id="stopBtn">■ STOP</button>
          </div>
          <span id="userLabel" style="color:var(--muted);font-size:12px;margin-left:8px"></span>
        </header>

        <main id="sectionContainer" role="main"></main>
      </div>
    </div>
  `;

  const auth = store.get('auth');
  const userLabel = document.getElementById('userLabel');
  userLabel.textContent = auth.username ? `@${auth.username}` : '';

  // Navigation
  document.querySelectorAll('.nav-link[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => navigateTo(btn.dataset.tab));
  });

  // Logout
  document.getElementById('logoutBtn').addEventListener('click', async () => {
    await api.logout();
    store.set('auth', { authenticated: false });
    showLogin();
  });

  // START/STOP — real runtime control
  document.getElementById('startBtn').addEventListener('click', async () => {
    const btn = document.getElementById('startBtn');
    btn.disabled = true;
    const r = await api.runtime.start();
    btn.disabled = false;
    if (r.ok) {
      toast.success('Runtime started');
    } else {
      toast.error('START lỗi: ' + r.error);
    }
    updateTopbarHealth();
  });

  document.getElementById('stopBtn').addEventListener('click', async () => {
    const btn = document.getElementById('stopBtn');
    btn.disabled = true;
    const r = await api.runtime.stop();
    btn.disabled = false;
    if (r.ok) {
      toast.success(`Đã dừng (${r.data.cancelled} jobs hủy)`);
    } else {
      toast.error('STOP lỗi: ' + r.error);
    }
    updateTopbarHealth();
  });

  // Restore hash routing
  const hash = location.hash.replace('#', '');
  const targetTab = TABS.find(t => t.id === hash)?.id || activeTab;
  navigateTo(targetTab);

  // Health polling
  updateTopbarHealth();
  setInterval(updateTopbarHealth, 30000);
}

let _currentTab = null;

function navigateTo(tabId) {
  if (!TABS.find(t => t.id === tabId)) tabId = 'dashboard';

  if (_currentTab === 'logs') destroyLogs();

  _currentTab = tabId;
  store.setPref('activeTab', tabId);
  location.hash = tabId;

  document.querySelectorAll('.nav-link[data-tab]').forEach(btn => {
    const isActive = btn.dataset.tab === tabId;
    btn.classList.toggle('active', isActive);
    btn.setAttribute('aria-current', isActive ? 'page' : 'false');
  });

  const container = document.getElementById('sectionContainer');

  switch (tabId) {
    case 'dashboard': renderDashboard(container); break;
    case 'topics': renderMappings(container); break;
    case 'channels': renderChannels(container); break;
    case 'telegram': renderTelegram(container); break;
    case 'import': renderBackup(container); break;
    case 'logs': renderLogs(container); break;
    default: renderDashboard(container);
  }
}

async function updateTopbarHealth() {
  const badge = document.getElementById('topbarHealth');
  if (!badge) return;

  const r = await api.health();
  if (!r.ok) {
    badge.className = 'status-badge error';
    badge.innerHTML = '<span class="status-dot"></span> Backend offline';
    return;
  }

  const h = r.data;
  if (h.degraded) {
    badge.className = 'status-badge warning';
    badge.innerHTML = '<span class="status-dot"></span> Degraded';
  } else if (h.telegram_connected) {
    badge.className = 'status-badge live';
    badge.innerHTML = `<span class="status-dot"></span> Live${h.telegram_username ? ' @' + h.telegram_username : ''}`;
  } else {
    badge.className = 'status-badge warning';
    badge.innerHTML = '<span class="status-dot"></span> No Telegram';
  }

  store.set('health', h);
}

// -----------------------------------------------------------------------
// Bootstrap
// -----------------------------------------------------------------------

async function bootstrap() {
  const res = await api.authStatus();
  if (res.ok && res.data?.authenticated) {
    store.set('auth', {
      authenticated: true,
      username: res.data.username,
      role: res.data.role,
    });
    showApp();
  } else {
    showLogin();
  }
}

bootstrap();
