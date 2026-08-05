(() => {
  'use strict';

  const ENDPOINT = '/api/activity';
  const VISITOR_KEY = 'dpia-visitor-id';
  const HEARTBEAT_MS = 15000;
  const randomId = () => {
    if (crypto && typeof crypto.randomUUID === 'function') return crypto.randomUUID();
    return Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);
  };

  let visitorId;
  try {
    visitorId = localStorage.getItem(VISITOR_KEY) || randomId();
    localStorage.setItem(VISITOR_KEY, visitorId);
  } catch (_) {
    visitorId = randomId();
  }

  const sessionId = randomId();
  const startedAt = performance.now();
  let visibleSince = document.visibilityState === 'visible' ? startedAt : null;
  let visibleTotal = 0;
  let lastSentDuration = -1;

  const visibleDuration = () => {
    const current = visibleSince === null ? 0 : performance.now() - visibleSince;
    return Math.max(0, Math.round(visibleTotal + current));
  };

  const optionalValue = (key, queryNames) => {
    try {
      const stored = localStorage.getItem(key);
      if (stored) return stored;
    } catch (_) {}
    const query = new URLSearchParams(location.search);
    for (const name of queryNames) {
      if (query.get(name)) return query.get(name);
    }
    return null;
  };

  const payload = event => ({
    event,
    visitor_id: visitorId,
    session_id: sessionId,
    duration_ms: visibleDuration(),
    path: location.pathname + location.search,
    language: navigator.language || document.documentElement.lang || null,
    postal_code: optionalValue('dpia-postal-code', ['postal_code', 'codigoPostal']),
    latitude: optionalValue('dpia-latitude', ['latitude', 'lat']),
    longitude: optionalValue('dpia-longitude', ['longitude', 'lng'])
  });

  const send = (event, finalEvent = false) => {
    const data = payload(event);
    if (event === 'heartbeat' && data.duration_ms === lastSentDuration) return;
    lastSentDuration = data.duration_ms;
    const body = JSON.stringify(data);

    if (finalEvent && navigator.sendBeacon) {
      navigator.sendBeacon(ENDPOINT, new Blob([body], {type: 'application/json'}));
      return;
    }
    fetch(ENDPOINT, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body,
      keepalive: finalEvent,
      credentials: 'same-origin'
    }).catch(() => {});
  };

  document.addEventListener('visibilitychange', () => {
    const now = performance.now();
    if (document.visibilityState === 'hidden' && visibleSince !== null) {
      visibleTotal += now - visibleSince;
      visibleSince = null;
      send('visibility', true);
    } else if (document.visibilityState === 'visible' && visibleSince === null) {
      visibleSince = now;
      send('visibility');
    }
  });

  window.addEventListener('pagehide', () => {
    if (visibleSince !== null) {
      visibleTotal += performance.now() - visibleSince;
      visibleSince = null;
    }
    send('page_exit', true);
  });

  send('session_start');
  window.setInterval(() => {
    if (document.visibilityState === 'visible') send('heartbeat');
  }, HEARTBEAT_MS);
})();
