(() => {
  'use strict';
  const clear = () => { sessionStorage.removeItem('participants-admin-token'); sessionStorage.removeItem('participants-admin-credentials'); };
  async function request(url, options = {}) {
    const headers = {'Content-Type':'application/json', ...(options.headers || {})};
    const token = sessionStorage.getItem('participants-admin-token');
    if (token) headers.Authorization = 'Bearer ' + token;
    else {
      let credentials;
      try { credentials = JSON.parse(sessionStorage.getItem('participants-admin-credentials') || 'null'); } catch (_) {}
      if (!credentials) { location.replace('/login'); throw new Error('Inicia sesión'); }
      headers.Authorization = 'Basic ' + btoa(unescape(encodeURIComponent(credentials.email + ':' + credentials.password)));
    }
    const response = await fetch(url, {...options, headers});
    const data = await response.json().catch(() => ({}));
    if (response.status === 401) { clear(); location.replace('/login'); }
    if (!response.ok) throw new Error(data.error || 'No se pudo completar la operación');
    return data;
  }
  async function ready(webOnly = false) {
    const status = document.getElementById('adminAccessStatus');
    try {
      const result = await request('/admin/api/access');
      document.querySelectorAll('[data-web-permission]').forEach(link => { link.hidden = !result.permissions.web_leads; });
      if (webOnly && !result.permissions.web_leads) throw new Error('Acceso reservado a administradores y moderadores');
      if (status) status.textContent = '';
      const content = document.getElementById('adminContent');
      if (content) content.hidden = false;
      return true;
    } catch (error) { if (status) status.textContent = error.message; return false; }
  }
  document.getElementById('adminLogout')?.addEventListener('click', async () => {
    try { await request('/auth/logout', {method:'POST'}); } catch (_) {}
    clear(); location.href = '/login';
  });
  window.DPIAAdmin = {request, ready};
})();
