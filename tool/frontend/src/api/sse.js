/**
 * SSE client with reconnect, Last-Event-ID support and heartbeat handling.
 * No secrets in any SSE message — enforced by backend.
 */

export class JobSSE {
  constructor(jobId, onEvent) {
    this.jobId = jobId;
    this.onEvent = onEvent;
    this._lastEventId = null;
    this._es = null;
    this._reconnectDelay = 1000;
    this._maxDelay = 30000;
    this._closed = false;
    this._connect();
  }

  _connect() {
    if (this._closed) return;
    const url = new URL(`/api/sse/jobs/${this.jobId}`, window.location.href);
    if (this._lastEventId) {
      url.searchParams.set('last_event_id', this._lastEventId);
    }

    this._es = new EventSource(url.toString(), { withCredentials: true });

    this._es.addEventListener('message', (e) => {
      this._reconnectDelay = 1000; // reset on success
      if (e.lastEventId) this._lastEventId = e.lastEventId;
      try {
        const data = JSON.parse(e.data);
        this.onEvent(data);
      } catch { /* ignore malformed events */ }
    });

    this._es.addEventListener('heartbeat', () => {
      // keep-alive — no action needed
    });

    this._es.onerror = () => {
      this._es.close();
      if (!this._closed) {
        setTimeout(() => this._connect(), this._reconnectDelay);
        this._reconnectDelay = Math.min(this._reconnectDelay * 2, this._maxDelay);
      }
    };
  }

  close() {
    this._closed = true;
    if (this._es) this._es.close();
  }
}

export class LogSSE {
  constructor(onEntry) {
    this.onEntry = onEntry;
    this._es = null;
    this._closed = false;
    this._reconnectDelay = 2000;
    this._connect();
  }

  _connect() {
    if (this._closed) return;
    this._es = new EventSource('/api/sse/logs', { withCredentials: true });

    this._es.addEventListener('log', (e) => {
      this._reconnectDelay = 2000;
      try {
        this.onEntry(JSON.parse(e.data));
      } catch { /* ignore */ }
    });

    this._es.onerror = () => {
      this._es.close();
      if (!this._closed) {
        setTimeout(() => this._connect(), this._reconnectDelay);
        this._reconnectDelay = Math.min(this._reconnectDelay * 2, 30000);
      }
    };
  }

  close() {
    this._closed = true;
    if (this._es) this._es.close();
  }
}
