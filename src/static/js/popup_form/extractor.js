(function () {
  const qs = (s, r=document) => r.querySelector(s);
  const qsa = (s, r=document) => [...r.querySelectorAll(s)];

  // Mapa TLD por marketplace (para los que lo usan)
  const TLD = { ES:'es', IT:'it', DE:'de', US:'com' };

  // ====== AMAZON ======
  function extractASIN(url){
    const m1 = url.match(/\/dp\/([A-Z0-9]{10})(?=[/?&#]|$)/i);
    if (m1) return m1[1].toUpperCase();
    const m2 = url.match(/\/gp\/(?:product|aw\/d)\/([A-Z0-9]{10})(?=[/?&#]|$)/i);
    if (m2) return m2[1].toUpperCase();
    const m3 = url.match(/[?&]ASIN=([A-Z0-9]{10})/i);
    if (m3) return m3[1].toUpperCase();
    const m4 = url.match(/(B0[A-Z0-9]{8})/i);
    if (m4) return m4[1].toUpperCase();
    return null;
  }
  function buildAmazonCleanUrl(asin, tag, market){
    const tld = TLD[market] || 'es';
    return `https://www.amazon.${tld}/dp/${asin}?tag=${encodeURIComponent(tag)}`;
  }
  // Imagen oficial vía sistema de anuncios (evita scraping)
  function buildAmazonImgUrl(asin, tag, market, sizePx){
    const mp = market || 'ES'; // ES/IT/DE/US
    const px = Math.max(120, Math.min(parseInt(sizePx||500,10), 2000));
    return `https://ws-eu.amazon-adsystem.com/widgets/q?_encoding=UTF8&ASIN=${asin}&Format=_SL${px}_&ID=AsinImage&MarketPlace=${mp}&ServiceVersion=20070822&WS=1&tag=${encodeURIComponent(tag)}`;
  }

  // ====== ALIEXPRESS (básico: usa ?aff_fcid o ?aff_fsk si tienes program) ======
  function buildAliExpress(url, tag){
    // limpia y añade tu tracking genérico
    const u = new URL(url);
    u.searchParams.set('aff_fcid', tag);
    u.searchParams.set('aff_fsk', tag);
    return { clean: u.toString(), img: '' }; // imagen: mejor la subas tú o uses su API de afiliados
  }

  // ====== WALMART (Impact/Rakuten generan links ya con tracking) ======
  function buildWalmart(url, tag){
    // si tienes deep-link de Impact, simplemente asegura el pid/subid
    const u = new URL(url);
    if (!u.hostname.includes('walmart')) return { clean: url, img: '' };
    // placeholder: si usas Impact, agrega subId
    u.searchParams.set('subId', tag);
    return { clean: u.toString(), img: '' };
  }

  // ====== EBAY (EPN) ======
  function buildEbay(url, tag){
    // si usas ePN: campid, customid
    const u = new URL(url);
    u.searchParams.set('customid', tag);
    return { clean: u.toString(), img: '' };
  }

  // ====== ALLEGRO (PL) ======
  function buildAllegro(url, tag){
    // Allegro Ads/eVentures: depende del programa — dejamos sub_id como placeholder
    const u = new URL(url);
    u.searchParams.set('utm_source', 'dpia');
    u.searchParams.set('utm_medium', 'aff');
    u.searchParams.set('utm_campaign', tag);
    return { clean: u.toString(), img: '' };
  }

  // ====== UI wiring ======
  function openModal(){ qs('#dpiaExtractorModal').hidden = false; }
  function closeModal(){ qs('#dpiaExtractorModal').hidden = true; }

  function convert(){
    const platform = qs('#exPlatform').value;
    const market = qs('#exMarket').value;
    const tag = (qs('#exTag').value || '').trim();
    const size = qs('#exImgSize').value;
    const raw = (qs('#exRawUrl').value || '').trim();

    if (!raw) { alert('Pegá la URL original.'); return; }

    let clean='', img='', html='';
    if (platform === 'amazon'){
      const asin = extractASIN(raw);
      if (!asin) { alert('No pude extraer el ASIN de Amazon.'); return; }
      const cleanUrl = buildAmazonCleanUrl(asin, tag || 'dpiaweb-21', market);
      const imgUrl = buildAmazonImgUrl(asin, tag || 'dpiaweb-21', market, size);
      clean = cleanUrl; img = imgUrl;
      html = `<a href="${cleanUrl}" target="_blank" rel="noopener noreferrer">\n  <img src="${imgUrl}" alt="Amazon ASIN ${asin}" />\n</a>`;
    } else if (platform === 'aliexpress'){
      const r = buildAliExpress(raw, tag || 'dpia');
      clean = r.clean; img = r.img;
      html = `<a href="${clean}" target="_blank" rel="noopener noreferrer">Ver en AliExpress</a>`;
    } else if (platform === 'walmart'){
      const r = buildWalmart(raw, tag || 'dpia');
      clean = r.clean; img = r.img;
      html = `<a href="${clean}" target="_blank" rel="noopener noreferrer">Ver en Walmart</a>`;
    } else if (platform === 'ebay'){
      const r = buildEbay(raw, tag || 'dpia');
      clean = r.clean; img = r.img;
      html = `<a href="${clean}" target="_blank" rel="noopener noreferrer">Ver en eBay</a>`;
    } else if (platform === 'allegro'){
      const r = buildAllegro(raw, tag || 'dpia');
      clean = r.clean; img = r.img;
      html = `<a href="${clean}" target="_blank" rel="noopener noreferrer">Ver en Allegro</a>`;
    }

    qs('#exCleanUrl').value = clean;
    qs('#exImgUrl').value = img;
    qs('#exHtmlSnippet').value = html;

    const prevLink = qs('#exPreviewLink');
    const prevImg  = qs('#exPreviewImg');
    prevLink.href = clean || '#';
    prevImg.src = img || '';
    qs('#exApplyToForm').disabled = !clean;
  }

  function applyToForm(){
    const href = qs('#exCleanUrl').value;
    const img  = qs('#exImgUrl').value;
    const hrefInput = qs('input[name="href"]');
    const imgInput  = qs('input[name="image"]');
    if (hrefInput) hrefInput.value = href;
    if (imgInput && img) imgInput.value = img;
    // refresca tu preview si tu app expone esta función
    if (window.DPIA && typeof window.DPIA.updatePreview === 'function'){
      window.DPIA.updatePreview(true);
    }
    closeModal();
  }

  // Events
  window.addEventListener('DOMContentLoaded', () => {
    const btn = qs('#btnOpenExtractor');
    if (btn) btn.addEventListener('click', openModal);
    qsa('[data-close]').forEach(el => el.addEventListener('click', closeModal));
    const modal = qs('#dpiaExtractorModal');
    if (modal) modal.addEventListener('keydown', (e)=>{ if(e.key==='Escape') closeModal(); });
    const conv = qs('#exConvert'); if (conv) conv.addEventListener('click', convert);
    const apply = qs('#exApplyToForm'); if (apply) apply.addEventListener('click', applyToForm);
  });
})();
