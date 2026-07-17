// static/js/popup_form/popup_form.js
(function () {
  const state = (window.DPIA = window.DPIA || {}).state || (window.DPIA.state = { lang: "es" });

  const form = document.getElementById('popupForm');
  const anchor = document.getElementById('previewAnchor');
  const sizeBadge = document.getElementById('sizeBadge');
  const errorsBox = document.getElementById('formErrors');

  function formToJSON(formEl) {
    
    const data = Object.fromEntries(new FormData(formEl).entries());
    data.width = parseInt(data.width || 0, 10);
    data.height = parseInt(data.height || 0, 10);
    data.prioritario = parseInt(data.prioritario || 0, 10);
    data.activo = data.activo === "1";
    return data;
  }

  function validate(data){
    const t = window.DPIA.$t;
    const errs=[];
      // email
    if(!data.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) errs.push(t("email"));
    if(!data.dominio) errs.push(t("domain"));
    if(!data.categoria) errs.push(t("category"));
    if(!data.lang) errs.push(t("lang"));
    if(!data.title) errs.push(t("titleLabel"));
    if(!data.href || !/^https?:\/\//i.test(data.href)) errs.push(t("href"));
    if(!data.image || !/^https?:\/\//i.test(data.image)) errs.push(t("image"));
    if(!data.width || data.width<50) errs.push(t("width"));
    if(!data.height || data.height<30) errs.push(t("height"));
    return errs;
  }

  function showErrors(errs){
    const t = window.DPIA.$t;
    if(!errs.length){ errorsBox.hidden=true; errorsBox.innerHTML=""; return; }
    errorsBox.hidden=false;
    errorsBox.innerHTML = `<strong>${t("errorsTitle")}</strong><ul>${errs.map(e=>`<li>${e}</li>`).join("")}</ul>`;
  }

  function renderLocal(anchorEl,data){
    const t = window.DPIA.$t;
    if(!data || !data.image || !data.href) {
      anchorEl.innerHTML = `<div class="placeholder">${t("placeholder")}</div>`;
      return;
    }
    anchorEl.innerHTML = `
      <div class="dpia-popup" style="position:relative;display:inline-block">
        <button class="dpia-popup-close"
                style="position:absolute;top:6px;right:6px;border:none;
                       background:rgba(0,0,0,.6);color:#fff;border-radius:8px;
                       padding:4px 8px;cursor:pointer">✖</button>
        <a href="${data.href}" target="_blank" rel="noopener">
          <img src="${data.image}" alt="${data.title||'Ad'}"
               style="display:block;width:${data.width||400}px;height:${data.height||600}px;border-radius:12px"/>
        </a>
      </div>`;
    anchorEl.querySelector(".dpia-popup-close").addEventListener("click", e=>{
      e.preventDefault(); anchorEl.innerHTML = `<div class="placeholder">${t("placeholder")}</div>`;
    });
  }

  function updatePreview(auto=false){
    const data = formToJSON(form);
    if (sizeBadge) sizeBadge.textContent = `${data.width||0}×${data.height||0}`;
    if (anchor){
      anchor.setAttribute('data-width', data.width);
      anchor.setAttribute('data-height', data.height);
    }
    if(auto){
      const errs = validate(data);
      showErrors(errs);
      if(errs.length) return;
    }
    renderLocal(anchor, {
      found:true, href:data.href, image:data.image, title:data.title,
      width:data.width, height:data.height
    });
  }

  // Exponer en window para que puedas llamarlas
  window.DPIA.formToJSON = formToJSON;
  window.DPIA.validate = validate;
  window.DPIA.updatePreview = updatePreview;


  

  // Listeners propios (si están los botones)
  const autoPreview = document.getElementById('autoPreview');
  const btnPreview = document.getElementById('btnPreview');
  const btnGuardar = document.getElementById('btnGuardar');




form && document.getElementById('autoPreview') &&
form.addEventListener('input', () => {
  if (document.getElementById('autoPreview').checked) {
    updatePreview(true); // valida y renderiza
  }
});



  autoPreview && autoPreview.addEventListener('change', (e)=>{ if(e.target.checked) updatePreview(true); });
  btnPreview && btnPreview.addEventListener('click', ()=>{
    const data=formToJSON(form); const errs=validate(data);
    showErrors(errs); if(errs.length) return; updatePreview();
  });
 // --- Guardar con AJAX clásico (form-url-encoded, sin preflight) ---
btnGuardar && btnGuardar.addEventListener('click', function(){
  const data = formToJSON(form);
  const errs = validate(data);
  showErrors(errs);
  if (errs.length) return;

  // defensa extra: rechazar data:
  if (String(data.image || '').startsWith('data:')) {
    alert('❌ La imagen no puede ser data: base64. Subila y usa la URL http(s).');
    return;
  }

  btnGuardar.disabled = true;
  btnGuardar.textContent = '⏳ Guardando...';

  // Same-origin: podemos usar JSON sin preflight ni CORS
  $.ajax({
    url: '/admin/popup',               // usa '/api/admin/popup' si tu BP tiene /api
    method: 'POST',
    contentType: 'application/json',
    data: JSON.stringify(data),
   success: function(resp){
          if (!resp || !resp.ok) {
            alert('❌ ' + ((resp && resp.error) || 'Error'));
            return;
          }

          // Mapeo backend -> preview
          const p = resp.popup || {};
          const previewData = {
            href:   p.link || (formToJSON(form).href),
            image:  p.imagen_url || (formToJSON(form).image),
            title:  p.titulo || (formToJSON(form).title),
            width:  p.medida_ancho || (formToJSON(form).width),
            height: p.medida_alto  || (formToJSON(form).height)
          };

          // Actualiza atributos del anchor y renderiza
          if (anchor) {
            anchor.setAttribute('data-width',  previewData.width);
            anchor.setAttribute('data-height', previewData.height);
          }
          renderLocal(anchor, previewData);

          // Snippets visibles y refrescados
          if (window.DPIA?.showSnippets) window.DPIA.showSnippets();
          if (window.DPIA?.updateSnippets) window.DPIA.updateSnippets();

          alert('✅ Guardado y previsualizado');
        },

    error: function(xhr){
      console.error('HTTP', xhr.status, xhr.responseText);
      alert('❌ Error HTTP ' + xhr.status);
    },
    complete: function(){
      btnGuardar.disabled = false;
      btnGuardar.textContent = '💾 Guardar';
    }
  });
});



})();























(function(){
  // ===== Builder de snippets =====
  function buildHost() {
    const sel = document.getElementById('snippetHost');
    const chosen = sel ? sel.value : 'auto';
    if (chosen && chosen !== 'auto') return chosen;

    // AUTO: usa el origen del embed.js si existe, o el del documento
    const scriptTag = document.querySelector('script[src*="embed.js"]');
    if (scriptTag) {
      try { return new URL(scriptTag.src).origin; } catch (e) {}
    }
    return location.origin; // último recurso
  }

  function buildScriptSnippet(host, test = true) {
    // En producción, cambiá test=false
    const apiUrl = `${host}/api/popup${test ? '?test=1' : ''}/`;
    const embedSrc = `${host}/static/js/embed.js/`;

    // Si tu embed.js ya hace autodetección de host con rutas relativas, podés usar data-api="/api/popup"
    return [
      `<script`,
      `  src="${embedSrc}"`,
      `  data-api="${apiUrl}"`,
      `  defer>`,
      `</script>`
    ].join('\n');
  }

function buildDivSnippet(data) {
  const usaIds = !!(data.ambito_id && data.categoria_id);

  const attrs = [
    `class="dpia-popup-anchor"`,
    usaIds
      ? `data-ambito-id="${data.ambito_id}"`
      : `data-dominio="${data.dominio || ''}"`,
    usaIds
      ? `data-categoria-id="${data.categoria_id}"`
      : `data-categoria="${data.categoria || ''}"`,
    // 👇 SIEMPRE incluir el idioma
    `data-lang="${data.lang || ''}"`,
    data.cp ? `data-cp="${data.cp}"` : null,
    `data-width="${data.width || 800}"`,
    `data-height="${data.height || 200}"`,
    `data-placeholder-color="#7CFC00"`
  ].filter(Boolean).join(' ');

  return `<div ${attrs}></div>`;
}


  function updateSnippets() {
    const data = (window.DPIA && window.DPIA.formToJSON)
      ? window.DPIA.formToJSON(document.getElementById('popupForm'))
      : null;
    if (!data) return;

    const host = buildHost();
    const scriptCode = buildScriptSnippet(host, /*test*/ true);
    const divCode = buildDivSnippet(data);

    const scriptEl = document.getElementById('scriptSnippet');
    const divEl = document.getElementById('divSnippet');
    if (scriptEl) scriptEl.textContent = scriptCode;
    if (divEl) divEl.textContent = divCode;
  }

function showSnippets() {
  const box = document.getElementById('snippetBox');
  if (box) { box.style.display = 'block'; }
  if (window.DPIA?.applyI18n) window.DPIA.applyI18n();   // ⬅️ importante
  updateSnippets();
}


  // Exponemos helpers para usarlos desde otros módulos
  window.DPIA = window.DPIA || {};
  window.DPIA.updateSnippets = updateSnippets;
  window.DPIA.showSnippets = showSnippets;

  // ===== Eventos de UI =====
  document.getElementById('snippetHost')?.addEventListener('change', updateSnippets);

  document.getElementById('copyScript')?.addEventListener('click', async ()=>{
    const code = document.getElementById('scriptSnippet').textContent;
    await navigator.clipboard.writeText(code);
    alert('Copiado el <script> ✅');
  });

  document.getElementById('copyDiv')?.addEventListener('click', async ()=>{
    const code = document.getElementById('divSnippet').textContent;
    await navigator.clipboard.writeText(code);
    alert('Copiado el <div> ✅');
  });

  // Si se modifica el formulario y está visible el bloque de snippets, los refrescamos
  document.getElementById('popupForm')?.addEventListener('input', ()=>{
    const box = document.getElementById('snippetBox');
    if (box && box.style.display !== 'none') updateSnippets();
  });
})();
