/**
 * Modal dialog component.
 * Closes on Escape, overlay click, and explicit close button.
 */

export function createModal({ title, body, footer, onClose } = {}) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');

  const modal = document.createElement('div');
  modal.className = 'modal';

  const header = document.createElement('div');
  header.className = 'modal-header';

  const titleEl = document.createElement('h3');
  titleEl.textContent = title || '';

  const closeBtn = document.createElement('button');
  closeBtn.className = 'btn btn-ghost btn-sm';
  closeBtn.textContent = '×';
  closeBtn.setAttribute('aria-label', 'Đóng');
  closeBtn.addEventListener('click', close);

  header.appendChild(titleEl);
  header.appendChild(closeBtn);
  modal.appendChild(header);

  if (body) {
    const bodyEl = document.createElement('div');
    bodyEl.className = 'modal-body';
    if (typeof body === 'string') {
      bodyEl.textContent = body;
    } else {
      bodyEl.appendChild(body);
    }
    modal.appendChild(bodyEl);
  }

  if (footer) {
    const footerEl = document.createElement('div');
    footerEl.className = 'modal-footer';
    footerEl.appendChild(footer);
    modal.appendChild(footerEl);
  }

  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close();
  });

  const escHandler = (e) => {
    if (e.key === 'Escape') close();
  };
  document.addEventListener('keydown', escHandler);

  function close() {
    document.removeEventListener('keydown', escHandler);
    overlay.remove();
    onClose?.();
  }

  return { overlay, modal, close };
}

export function confirm(message, { title = 'Xác nhận', confirmLabel = 'Xác nhận', danger = false } = {}) {
  return new Promise((resolve) => {
    const footer = document.createElement('div');
    footer.style.cssText = 'display:flex;gap:8px;justify-content:flex-end;width:100%';

    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn btn-secondary';
    cancelBtn.textContent = 'Hủy';

    const confirmBtn = document.createElement('button');
    confirmBtn.className = `btn ${danger ? 'btn-danger' : 'btn-primary'}`;
    confirmBtn.textContent = confirmLabel;

    footer.appendChild(cancelBtn);
    footer.appendChild(confirmBtn);

    const bodyEl = document.createElement('p');
    bodyEl.textContent = message;
    bodyEl.style.color = 'var(--text)';

    const { close } = createModal({
      title,
      body: bodyEl,
      footer,
      onClose: () => resolve(false),
    });

    cancelBtn.addEventListener('click', () => { close(); resolve(false); });
    confirmBtn.addEventListener('click', () => { close(); resolve(true); });
  });
}
