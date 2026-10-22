(async () => {
  'use strict';
  const admin = window.DPIAAdmin;
  if (!await admin.ready(true)) return;
  const $ = id => document.getElementById(id);
  const dialog = $('leadDialog'), editor = $('leadEditor'), body = $('leadsBody');
  const fieldNames = ['name','email','lang','business_type','solution_type','features','online_payments','ai','integration','integration_details','description'];
  let page = 1, total = 0, activeId = null, sequence = 0;
  const options = name => Object.fromEntries([...editor.elements[name].options].map(o => [o.value, o.textContent]));
  const businesses = options('business_type'), solutions = options('solution_type');
  function cell(row, text, className = '') {
    const el = document.createElement('td'); el.textContent = text; el.className = className; row.append(el); return el;
  }
  async function load() {
    const requestId = ++sequence;
    $('leadStatus').textContent = 'Cargando solicitudes…';
    try {
      const params = new URLSearchParams({q:$('leadSearch').value, business:$('businessFilter').value, solution:$('solutionFilter').value, page, per_page:25});
      const result = await admin.request('/admin/api/web-leads?' + params);
      if (requestId !== sequence) return;
      total = result.total;
      if (page > 1 && (page - 1) * 25 >= total) { page--; return load(); }
      body.replaceChildren();
      for (const item of result.items) {
        const tr = document.createElement('tr');
        cell(tr, item.name + '\n' + item.email, 'lead-description');
        cell(tr, (businesses[item.business_type] || item.business_type) + '\n' + (solutions[item.solution_type] || item.solution_type), 'lead-description');
        cell(tr, item.description.length > 180 ? item.description.slice(0,180) + '…' : item.description, 'lead-description');
        cell(tr, new Date(item.created_at).toLocaleString());
        const actions = cell(tr, '', 'actions');
        for (const [action,label] of [['view','Ver detalle'],['edit','Editar'],['delete','Eliminar']]) {
          const button = document.createElement('button'); button.type = 'button'; button.textContent = label;
          if (action === 'delete') button.className = 'danger';
          button.addEventListener('click', async () => {
            button.disabled = true;
            try {
              if (action === 'delete') {
                if (!confirm('¿Eliminar definitivamente la solicitud de ' + item.name + '?')) return;
                await admin.request('/admin/api/web-leads/' + encodeURIComponent(item.id), {method:'DELETE'});
                await load();
              } else {
                const data = await admin.request('/admin/api/web-leads/' + encodeURIComponent(item.id));
                openEditor(data.item, action === 'view');
              }
            } catch (error) { $('leadStatus').textContent = error.message; }
            finally { button.disabled = false; }
          });
          actions.append(button);
        }
        body.append(tr);
      }
      $('leadStatus').textContent = total ? total + ' solicitud(es).' : 'No hay solicitudes con estos filtros.';
      $('pageInfo').textContent = 'Página ' + page + ' de ' + Math.max(1,Math.ceil(total / 25));
      $('previousPage').disabled = page <= 1; $('nextPage').disabled = page * 25 >= total;
    } catch (error) { $('leadStatus').textContent = error.message; }
  }
  function openEditor(item = null, readonly = false) {
    editor.reset(); activeId = item?.id || null;
    for (const name of fieldNames) {
      const field = editor.elements[name]; field.disabled = readonly;
      if (item) field.value = name === 'lang' ? item.language : item[name] || '';
    }
    $('leadDialogTitle').textContent = readonly ? 'Detalle de solicitud' : item ? 'Editar solicitud' : 'Nueva solicitud';
    $('leadReference').textContent = item ? 'Referencia: ' + item.id + ' · Aviso aceptado: ' + item.privacy_version : '';
    $('consentRow').hidden = Boolean(item); editor.elements.privacy_consent.required = !item;
    $('saveLead').hidden = readonly; $('saveLead').disabled = false; $('editorStatus').textContent = '';
    dialog.showModal();
  }
  $('newLead').addEventListener('click', () => openEditor());
  $('closeEditor').addEventListener('click', () => dialog.close());
  editor.addEventListener('submit', async event => {
    event.preventDefault();
    if (!editor.reportValidity()) return;
    const payload = Object.fromEntries(fieldNames.map(name => [name, editor.elements[name].value]));
    if (!activeId) payload.privacy_consent = editor.elements.privacy_consent.checked;
    $('saveLead').disabled = true;
    try {
      await admin.request('/admin/api/web-leads' + (activeId ? '/' + encodeURIComponent(activeId) : ''), {method:activeId ? 'PATCH' : 'POST', body:JSON.stringify(payload)});
      dialog.close(); await load();
    } catch (error) { $('editorStatus').textContent = error.message; }
    finally { $('saveLead').disabled = false; }
  });
  $('leadFilters').addEventListener('submit', event => { event.preventDefault(); page = 1; load(); });
  for (const id of ['businessFilter','solutionFilter']) $(id).addEventListener('change', () => { page = 1; load(); });
  $('leadSearch').addEventListener('search', () => { page = 1; load(); });
  $('previousPage').addEventListener('click', () => { if (page > 1) { page--; load(); } });
  $('nextPage').addEventListener('click', () => { if (page * 25 < total) { page++; load(); } });
  await load();
})();
