/**
 * Minimal reactive state store.
 * localStorage used ONLY for non-sensitive preferences (theme, tab, collapse, filter).
 * Business data (channels, mappings, jobs) never goes to localStorage.
 */

const _listeners = {};
const _state = {
  // Auth — never persisted
  auth: { authenticated: false, username: null, role: null, csrfToken: null },

  // UI preferences — safe to persist
  prefs: {
    theme: 'dark',
    activeTab: 'dashboard',
    sidebarCollapsed: false,
    expandedMappings: {},
  },

  // Business data — from API only, never localStorage
  health: null,
  channels: [],
  mappings: [],
  jobs: [],
  bots: [],
  userbotStatus: null,
  backups: [],

  // Job SSE state
  activeJobId: null,
  jobProgress: {},

  // UI state
  loading: {},
  error: {},
};

// Load preferences from localStorage
try {
  const saved = localStorage.getItem('upbain_prefs');
  if (saved) {
    const parsed = JSON.parse(saved);
    // Only allow safe preference keys
    const safeKeys = ['theme', 'activeTab', 'sidebarCollapsed', 'expandedMappings'];
    safeKeys.forEach(k => {
      if (k in parsed) _state.prefs[k] = parsed[k];
    });
  }
} catch { /* ignore */ }

function savePrefs() {
  try {
    localStorage.setItem('upbain_prefs', JSON.stringify(_state.prefs));
  } catch { /* ignore */ }
}

function emit(key) {
  const fns = _listeners[key] || [];
  fns.forEach(fn => fn(_state[key]));
  const all = _listeners['*'] || [];
  all.forEach(fn => fn(key, _state[key]));
}

const store = {
  get: (key) => _state[key],

  set: (key, value) => {
    _state[key] = value;
    if (key === 'prefs') savePrefs();
    emit(key);
  },

  setPref: (key, value) => {
    _state.prefs = { ..._state.prefs, [key]: value };
    savePrefs();
    emit('prefs');
  },

  setLoading: (key, val) => {
    _state.loading = { ..._state.loading, [key]: val };
    emit('loading');
  },

  setError: (key, val) => {
    _state.error = { ..._state.error, [key]: val };
    emit('error');
  },

  on: (key, fn) => {
    _listeners[key] = _listeners[key] || [];
    _listeners[key].push(fn);
    return () => {
      _listeners[key] = (_listeners[key] || []).filter(f => f !== fn);
    };
  },
};

export default store;
