/**
 * Toast notification system.
 * Uses textContent — no XSS risk.
 */

let _container = null;

function getContainer() {
  if (!_container) {
    _container = document.createElement('div');
    _container.className = 'toast-container';
    document.body.appendChild(_container);
  }
  return _container;
}

export function showToast(message, type = 'info', duration = 4000) {
  const container = getContainer();
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const msg = document.createElement('span');
  msg.className = 'toast-msg';
  msg.textContent = message; // textContent — safe against XSS

  const close = document.createElement('button');
  close.className = 'toast-close';
  close.textContent = '×';
  close.setAttribute('aria-label', 'Đóng');
  close.addEventListener('click', () => dismiss(toast));

  toast.appendChild(msg);
  toast.appendChild(close);
  container.appendChild(toast);

  if (duration > 0) {
    setTimeout(() => dismiss(toast), duration);
  }

  return toast;
}

function dismiss(toast) {
  if (!toast.parentNode) return;
  toast.style.opacity = '0';
  toast.style.transform = 'translateY(8px)';
  toast.style.transition = 'all .2s';
  setTimeout(() => toast.parentNode?.removeChild(toast), 200);
}

export const toast = {
  success: (msg, d) => showToast(msg, 'success', d),
  error: (msg, d) => showToast(msg, 'error', d || 6000),
  warning: (msg, d) => showToast(msg, 'warning', d),
  info: (msg, d) => showToast(msg, 'info', d),
};
