/**
 * Unified API client — single origin, single response envelope.
 *
 * ALL responses follow: {ok: bool, data: any, error: string|null}
 * Callers must read .data — never raw JSON.
 *
 * CSRF token is read from the upbain_csrf cookie and sent as X-CSRF-Token header
 * on all state-changing requests (POST/PUT/PATCH/DELETE).
 */

const BASE = '/api';

function getCsrfToken() {
  const match = document.cookie.match(/upbain_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

async function request(method, path, body, options = {}) {
  const isStateChanging = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method.toUpperCase());
  const headers = { 'Content-Type': 'application/json' };

  if (isStateChanging) {
    const csrf = getCsrfToken();
    if (csrf) headers['X-CSRF-Token'] = csrf;
  }

  const fetchOpts = {
    method: method.toUpperCase(),
    headers,
    credentials: 'same-origin',
    ...options,
  };

  if (body !== undefined) {
    fetchOpts.body = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(`${BASE}${path}`, fetchOpts);
  } catch (err) {
    return { ok: false, data: null, error: `Network error: ${err.message}` };
  }

  // Handle 401 — redirect to login
  if (res.status === 401) {
    if (!window.location.pathname.includes('/login')) {
      window.location.href = '/#login';
    }
    return { ok: false, data: null, error: 'Not authenticated' };
  }

  let json;
  try {
    json = await res.json();
  } catch {
    return { ok: false, data: null, error: `HTTP ${res.status}: Invalid JSON response` };
  }

  // Enforce envelope: all responses must have {ok, data}
  if (typeof json !== 'object' || json === null || !('ok' in json)) {
    return { ok: false, data: null, error: 'Unexpected response format from server' };
  }

  if (!json.ok && res.status >= 400) {
    return { ok: false, data: null, error: json.error || json.detail || `HTTP ${res.status}` };
  }

  return json;
}

const api = {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, body),
  put: (path, body) => request('PUT', path, body),
  patch: (path, body) => request('PATCH', path, body),
  delete: (path) => request('DELETE', path),

  // Auth
  authStatus: () => api.get('/auth/status'),
  login: (username, password) => api.post('/auth/login', { username, password }),
  logout: () => api.post('/auth/logout'),

  // Health
  health: () => api.get('/health'),

  // Channels
  channels: {
    list: () => api.get('/channels'),
    add: (body) => api.post('/channels', body),
    get: (id) => api.get(`/channels/${id}`),
    updateMeta: (id, body) => api.patch(`/channels/${id}/meta`, body),
    checkLiveness: (id) => api.post(`/channels/${id}/check-liveness`),
    checkDead: (chatIds) => api.post('/channels/check-dead', { chat_ids: chatIds }),
    delete: (id) => api.delete(`/channels/${id}`),
  },

  // Mappings
  mappings: {
    list: () => api.get('/mappings'),
    create: (body) => api.post('/mappings', body),
    get: (id) => api.get(`/mappings/${id}`),
    update: (id, body) => api.put(`/mappings/${id}`, body),
    delete: (id) => api.delete(`/mappings/${id}`),
  },

  // Runtime
  runtime: {
    status: () => api.get('/runtime/status'),
    start: () => api.post('/runtime/start'),
    stop: () => api.post('/runtime/stop'),
    emergencyStop: () => api.post('/runtime/emergency-stop'),
    runMapping: (body) => api.post('/runtime/run-mapping', body),
    cancelJob: (id) => api.post(`/runtime/jobs/${id}/cancel`),
    jobs: (limit = 50) => api.get(`/runtime/jobs?limit=${limit}`),
    job: (id) => api.get(`/runtime/jobs/${id}`),
  },

  // Telegram
  telegram: {
    userbotStatus: () => api.get('/telegram/userbot/status'),
    saveConfig: (body) => api.post('/telegram/userbot/config', body),
    sendCode: (phone) => api.post('/telegram/userbot/send-code', { phone }),
    confirmCode: (body) => api.post('/telegram/userbot/confirm-code', body),
    confirm2FA: (password) => api.post('/telegram/userbot/confirm-2fa', { password }),
    logout: () => api.post('/telegram/userbot/logout'),
    listBots: () => api.get('/telegram/bots'),
    addBot: (body) => api.post('/telegram/bots', body),
    deleteBot: (id) => api.delete(`/telegram/bots/${id}`),
  },

  // Backup
  backup: {
    runNow: () => api.post('/backup/run-now'),
    list: () => api.get('/backup/list'),
    downloadUrl: (filename) => `${BASE}/backup/download/${encodeURIComponent(filename)}`,
  },
};

export default api;
