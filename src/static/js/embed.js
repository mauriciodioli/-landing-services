(function () {
  // ====== Meta & debug ======
  window.__DPIA_EMBED_VERSION__ = '2025-10-01';
  console.debug('[embed loaded]', window.__DPIA_EMBED_VERSION__);

  // ====== Utils ======
  const toItems = (j) => {
    if (Array.isArray(j)) return j;
    if (j && Array.isArray(j.items)) return j.items;
    if (j && j.found) return [j];
    if (j && Array.isArray(j.data)) return j.data;
    if (j && Array.isArray(j.results)) return j.results;
    return [];
  };

  const deDupById = (arr) => {
    const seen = new Set();
    return arr.filter(x => {
      const k = (x && (x.id ?? x.popup_id ?? x.slug ?? JSON.stringify(x))) + '';
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    });
  };

  const attr = (el, n) => el && el.getAttribute ? el.getAttribute(n) : null;

  // localizar SIEMPRE el <script> actual
  const SCRIPT = document.currentScript || (function () {
    const ss = document.getElementsByTagName('script');
    return ss[ss.length - 1] || null;
  })();

  // origen absoluto y API
  const origin = (SCRIPT && SCRIPT.src) ? new URL(SCRIPT.src).origin : location.origin;
  let apiBase = (attr(SCRIPT, 'data-api') || '/api/p');
  if (apiBase.startsWith('/')) apiBase = origin + apiBase; // absolutizar

  // defaults visuales (placeholder off por defecto)
  const DEFAULTS = {
    placeholderOn: (attr(SCRIPT, 'data-placeholder') || 'off').toLowerCase() === 'on',
    placeholderColor: attr(SCRIPT, 'data-placeholder-color') || '#ffd54f'
  };

  console.debug('[embed.js] origin=', origin, 'apiBase=', apiBase);

  // ====== UI helpers ======
  function showPlaceholder(anchor, color, msg) {
    const w = parseInt(attr(anchor, 'data-width') || '400', 10);
    const h = parseInt(attr(anchor, 'data-height') || '600', 10);
    anchor.innerHTML = `
      <div class="dpia-popup-placeholder"
           style="width:${w}px;height:${h}px;background:${color};
                  color:#111;font:600 14px/1.4 system-ui,Arial,sans-serif;
                  display:flex;align-items:center;justify-content:center;
                  border:3px dashed #111;border-radius:12px;text-align:center;">
        ${msg}
      </div>`;
  }

  function renderOne(anchor, item) {
    if (!item) return;
    const w = parseInt(attr(anchor, 'data-width') || '400', 10);
    const h = parseInt(attr(anchor, 'data-height') || '600', 10);
    const useItemRatio = (attr(anchor, 'data-use-item-ratio') || 'false').toLowerCase() === 'true';
    const ratio = (useItemRatio && item.width && item.height) ? `${item.width} / ${item.height}` : `${w} / ${h}`;
    const fit = (attr(anchor, 'data-fit') || 'cover').toLowerCase(); // cover | contain

    anchor.innerHTML = `
      <div class="dpia-popup" style="position:relative;display:block;width:100%">
        <button class="dpia-popup-close"
                style="position:absolute;top:6px;right:6px;border:none;
                       background:rgba(0,0,0,.6);color:#fff;border-radius:6px;
                       padding:4px 8px;cursor:pointer;z-index:2">✖</button>
        <a href="${item.href}" target="_blank" rel="noopener" style="display:block">
          <div style="width:100%;aspect-ratio:${ratio};">
            <img src="${item.image}" alt="${item.title || 'Ad'}"
                 style="width:100%;height:100%;display:block;border-radius:12px;object-fit:${fit}"/>
          </div>
        </a>
      </div>`;

    anchor.querySelector('.dpia-popup-close')?.addEventListener('click', (e) => {
      e.preventDefault();
      const card = anchor.closest('.popup-fake-card, .card-publicacion-admin, .card-publicacion, .card') || anchor;
      card.style.transition = 'opacity .15s ease';
      card.style.opacity = '0';
      setTimeout(() => card.remove(), 150);
    });
  }

 function renderMany(anchor, items){
  // Si el anchor está dentro de una tarjeta, clonamos la tarjeta para cada item.
  // Podés forzarlo con data-explode="card" (default). data-explode="inline" mantiene el grid dentro del mismo anchor.
  const explodeMode = (attr(anchor,'data-explode') || 'card').toLowerCase(); // 'card' | 'inline'
  const cardSel = '.popup-fake-card, .card-publicacion-admin, .card-publicacion, .card';
  const card = anchor.closest(cardSel);

  if (explodeMode === 'card' && card) {
    const parent = card.parentElement;
    let afterNode = card;

    items.forEach((it, idx) => {
      if (idx === 0) {
        // Primer item usa la tarjeta original
        anchor.innerHTML = '';
        renderOne(anchor, it);
        anchor.dataset.renderizado = 'true';
      } else {
        // Siguientes: clonar la tarjeta “plantilla”
        const clone = card.cloneNode(true);

        // limpiar y preparar el anchor del clon
        const cloneAnchor = clone.querySelector('.dpia-spot');
        if (cloneAnchor) {
          cloneAnchor.innerHTML = '';
          delete cloneAnchor.dataset.renderizado;
          renderOne(cloneAnchor, it);
          cloneAnchor.dataset.renderizado = 'true';
        }

        // insertar el clon como tarjeta hermana
        parent.insertBefore(clone, afterNode.nextSibling);
        afterNode = clone;
      }
    });
    return; // listo: uno por tarjeta
  }

  // Fallback: varios dentro del mismo anchor en un grid (modo inline)
  anchor.innerHTML = `<div class="dpia-popups-wrap" style="display:grid;gap:12px;"></div>`;
  const wrap = anchor.querySelector('.dpia-popups-wrap');

  // opcional: columnas vía data-cols
  const cols = parseInt(attr(anchor,'data-cols')||'0',10);
  if (cols > 0) wrap.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;

  items.forEach(it => {
    const holder = document.createElement('div');
    renderOne(holder, it);
    wrap.appendChild(holder.firstElementChild);
  });
}


  // ====== Param helpers ======
  function paramsFrom(anchor, globalDomain) {
    return {
      dominio:   attr(anchor, 'data-dominio')   || attr(anchor, 'data-ambito-id')    || globalDomain || '',
      categoria: attr(anchor, 'data-categoria') || attr(anchor, 'data-categoria-id') || '',
      lang:      attr(anchor, 'data-lang')      || attr(SCRIPT, 'data-lang')         || document.documentElement.lang || '',
      cp:        attr(anchor, 'data-cp')        || ''
    };
  }

  const keyOf = (p) => `${p.dominio}|${p.categoria}|${p.lang}|${p.cp}`;

  // data-count parser: "*", "all", número, vacío → sin límite
 function parseCountAttr(a) {
  const raw = (attr(a,'data-count') || '').trim().toLowerCase();
  if (raw === 'all' || raw === '*') return null;  // null = sin límite (explota en esa tarjeta)
  if (!raw) return 1;                             // ✅ DEFAULT: 1 popup por anchor
  const n = parseInt(raw, 10);
  return Number.isFinite(n) && n > 0 ? n : 1;     // si es inválido, cae a 1
}

  // llamada unificada (lista) con limit opcional
 function callList(params, limit) {
  const qs = [
    'list=1',
    (typeof limit === 'number' ? `limit=${encodeURIComponent(limit)}` : '')
  ].filter(Boolean).join('&');

  const url = apiBase + (apiBase.includes('?') ? '&' : '?') + qs;

  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params) // cp, dominio, categoria, lang
  });
}


  // ====== Core render (grupo) ======
  function fetchAndRenderGroup(group) {
    const { params, anchors } = group;

    // marcar para evitar doble render
    anchors.forEach(a => a.dataset.renderizado = 'true');

    // cuánto quiere cada anchor
    const needs = anchors.map(a => parseCountAttr(a));     // null = sin límite
      const allUnbounded = needs.every(n => n === null);
      const desiredTotal = allUnbounded
        ? null
        : needs.filter(n => typeof n === 'number').reduce((s, n) => s + n, 0);

    

    return callList(params, desiredTotal ?? undefined)
     .then(async (r) => {
        if (!r.ok) {
          const txt = await r.text().catch(()=>'(sin body)');
          throw new Error(`HTTP ${r.status} ${r.statusText} – ${txt}`);
        }
        return r.json();
      })

      .then(j => {
        const items = toItems(j);

        // SIN RESULTADOS → limpiar/remover
        if (!items.length) {
          anchors.forEach(a => {
            a.innerHTML = '';
            const card = a.closest('.popup-fake-card, .card-publicacion-admin, .card-publicacion, .card');
            if (card) card.remove();
          });
          return;
        }

        const allowDupGroup = anchors.some(a =>
          (attr(a, 'data-allow-duplicates') || 'false').toLowerCase() === 'true'
        );
        let pool = allowDupGroup ? items.slice(0) : deDupById(items);

        // pedido por anchor (null = all → todo lo que haya)
        const countsRequested = anchors.map(a => {
          const want = parseCountAttr(a);
          return want === null ? pool.length : want;
        });

        // sin duplicados → capear a lo disponible
        let counts = countsRequested.slice(0);
        if (!allowDupGroup) {
          let remaining = pool.length;
          counts = counts.map(c => {
            const take = Math.min(c, remaining);
            remaining -= take;
            return take;
          });
        }

        let cursor = 0;
        anchors.forEach((a, idx) => {
          const take = counts[idx];

          if (take <= 0) {
            const card = a.closest('.popup-fake-card, .card-publicacion-admin, .card-publicacion, .card') || a;
            card.remove();
            return;
          }

          let picked = [];
          if (allowDupGroup) {
            const n = Math.max(pool.length, 1);
            for (let i = 0; i < take; i++) picked.push(pool[(cursor + i) % n]);
            cursor = (cursor + take) % Math.max(pool.length, 1);
          } else {
            picked = pool.slice(cursor, cursor + take);
            cursor += take;
          }

          if (picked.length === 1) renderOne(a, picked[0]);
          else renderMany(a, picked);
        });
      })
      .catch((err) => {
  console.warn('[embed.js] LIST falló, fallback por anchor:', err);

  anchors.forEach(a => {
    const need = parseCountAttr(a); // null = sin límite

    const qs = [
      'list=1',
      (typeof need === 'number' ? `limit=${encodeURIComponent(need)}` : '')
    ].filter(Boolean).join('&');

    const url = apiBase + (apiBase.includes('?') ? '&' : '?') + qs;

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(group.params) // 👈 mantiene tus overrideParams
    })
    .then(r => r.json())
    .then(data => {
      const arr = toItems(data);
      if (!arr.length) { a.innerHTML = ''; return; }
      const take = (typeof need === 'number') ? need : arr.length;
      const slice = arr.slice(0, take);
      slice.length === 1 ? renderOne(a, slice[0]) : renderMany(a, slice);
    })
    .catch((e2) => {
      console.error('[embed.js] fallback por anchor también falló:', e2);
    });
  });
});

  }

  // ====== Auto init (render inicial desde data-*) ======
  function init() {
    const globalDomain = attr(SCRIPT, 'data-domain') || '';

    const anchors = Array
      .from(document.querySelectorAll('.dpia-spot'))
      .filter(a => !a.dataset.renderizado);

    // placeholder inmediato (si lo pediste)
    anchors.forEach(anchor => {
      if (DEFAULTS.placeholderOn) {
        const customColor = attr(anchor, 'data-placeholder-color') || DEFAULTS.placeholderColor;
        showPlaceholder(anchor, customColor, 'DPIA • POPUP');
      }
    });

    // agrupar por (dominio,categoria,lang,cp)
    const groups = new Map();
    anchors.forEach(a => {
      const p = paramsFrom(a, globalDomain);
      const k = keyOf(p);
      if (!groups.has(k)) groups.set(k, { params: p, anchors: [] });
      groups.get(k).anchors.push(a);
    });

    // pedir y renderizar
    groups.forEach(group => { fetchAndRenderGroup(group); });
  }

  // ====== API pública: re-render con overrides ======
  window.initEmbedPopups = function (overrideParams = {}) {
    const globalDomain = attr(SCRIPT, 'data-domain') || '';

    const anchors = Array
      .from(document.querySelectorAll('.dpia-spot'))
      .filter(a => !a.dataset.renderizado);

    const groups = new Map();
    anchors.forEach(a => {
      const p = paramsFrom(a, globalDomain);
      const merged = { ...p, ...overrideParams };
      const k = keyOf(merged);
      if (!groups.has(k)) groups.set(k, { params: merged, anchors: [] });
      groups.get(k).anchors.push(a);
    });

    groups.forEach(group => { fetchAndRenderGroup(group); });
  };

  // ====== Auto-run ======
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
