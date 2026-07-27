(() => {
  'use strict';

  const body = document.querySelector('#participantsBody');
  const statusMessage = document.querySelector('#statusMessage');
  const search = document.querySelector('#search');
  const courseFilter = document.querySelector('#courseFilter');
  const statusFilter = document.querySelector('#statusFilter');
  let rows = [];

  const token = () => {
    // Prefer stored credentials (email+password), fall back to token for backwards compatibility
    try {
      const credsJson = sessionStorage.getItem('participants-admin-credentials');
      if (credsJson) {
        const creds = JSON.parse(credsJson);
        return { type: 'basic', email: creds.email || '', password: creds.password || '' };
      }
    } catch (e) {}
    let tokenValue = sessionStorage.getItem('participants-admin-token');
    if (tokenValue) return { type: 'token', token: tokenValue };

    // Ask for email/password first (preferred)
    const email = window.prompt('Email de admin:') || '';
    if (email) {
      const password = window.prompt('Contraseña:') || '';
      if (password) {
        sessionStorage.setItem('participants-admin-credentials', JSON.stringify({ email, password }));
        return { type: 'basic', email, password };
      }
    }

    // Fallback: token prompt
    tokenValue = window.prompt('Token de administración (opcional):') || '';
    if (tokenValue) {
      sessionStorage.setItem('participants-admin-token', tokenValue);
      return { type: 'token', token: tokenValue };
    }
    return { type: 'none' };
  };

  const request = async (url, options = {}) => {
    const auth = token();
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    };
    if (auth.type === 'basic') {
      try {
        headers['Authorization'] = 'Basic ' + btoa(`${auth.email}:${auth.password}`);
      } catch (e) {}
    } else if (auth.type === 'token') {
      headers['X-Admin-Token'] = auth.token;
      headers['Authorization'] = 'Bearer ' + auth.token;
    }
    const response = await fetch(url, {
      ...options,
      headers,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    return payload;
  };

  const escapeHtml = value => String(value ?? '').replace(
    /[&<>"']/g,
    char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char])
  );

  const formatDate = value => value
    ? new Intl.DateTimeFormat('es', {dateStyle:'short', timeStyle:'short'}).format(new Date(value))
    : 'Sin definir';

  function render() {
    body.innerHTML = rows.map(row => `
      <tr>
        <td><strong>${escapeHtml(row.name)}</strong><a href="mailto:${escapeHtml(row.email)}">${escapeHtml(row.email)}</a><small>${escapeHtml(row.phone || 'Sin teléfono')} · ${escapeHtml(row.profile || 'Sin perfil')}</small></td>
        <td><strong>${escapeHtml(row.course_title)}</strong><small>${escapeHtml(row.company || row.job_title || '')}</small></td>
        <td><span>Curso: ${formatDate(row.course_date)}</span><small>Registro: ${formatDate(row.registered_at)}</small></td>
        <td><span>${escapeHtml(row.ip_address || 'Sin IP')}</span><small>${escapeHtml(row.utm_source || row.source || 'Directo')}</small></td>
        <td><span class="badge">${escapeHtml(row.status)}</span><small>Confirmación: ${row.confirmation_sent_at ? 'sí' : 'no'} · Recordatorio: ${row.reminder_sent_at ? 'sí' : 'no'}</small></td>
        <td class="actions">
          <button data-action="edit" data-id="${row.id}">Editar</button>
          <button data-action="confirm" data-id="${row.id}">Confirmación</button>
          <button data-action="remind" data-id="${row.id}">Recordatorio</button>
          <button class="danger" data-action="delete" data-id="${row.id}">Eliminar</button>
        </td>
      </tr>`).join('');
    document.querySelector('#totalParticipants').textContent = rows.length;
    document.querySelector('#totalConfirmed').textContent = rows.filter(row => row.confirmation_sent_at).length;
    document.querySelector('#totalReminders').textContent = rows.filter(row => row.reminder_sent_at).length;
  }

  async function load() {
    statusMessage.textContent = 'Cargando…';
    const params = new URLSearchParams();
    if (search.value.trim()) params.set('q', search.value.trim());
    if (courseFilter.value) params.set('course', courseFilter.value);
    if (statusFilter.value) params.set('status', statusFilter.value);
    try {
      const payload = await request(`/api/course-participants?${params}`);
      rows = payload.participants;
      render();
      statusMessage.textContent = `${rows.length} participante(s).`;
    } catch (error) {
      statusMessage.textContent = error.message;
    }
  }

  body.addEventListener('click', async event => {
    const button = event.target.closest('button[data-action]');
    if (!button) return;
    const id = Number(button.dataset.id);
    const row = rows.find(item => item.id === id);
    if (!row) return;
    try {
      if (button.dataset.action === 'edit') {
        const courseDate = window.prompt('Fecha del curso (AAAA-MM-DDTHH:MM):', row.course_date?.slice(0,16) || '');
        if (courseDate === null) return;
        const status = window.prompt('Estado (registered, cancelled, completed):', row.status);
        if (status === null) return;
        const notes = window.prompt('Notas internas:', row.notes || '');
        if (notes === null) return;
        await request(`/api/course-participants/${id}`, {
          method: 'PATCH',
          body: JSON.stringify({course_date: courseDate || null, status, notes}),
        });
      } else if (button.dataset.action === 'confirm') {
        await request(`/api/course-participants/${id}/confirmation`, {method:'POST'});
      } else if (button.dataset.action === 'remind') {
        await request(`/api/course-participants/${id}/reminder`, {method:'POST'});
      } else if (button.dataset.action === 'delete') {
        if (!window.confirm(`¿Eliminar definitivamente a ${row.name}?`)) return;
        await request(`/api/course-participants/${id}`, {method:'DELETE'});
      }
      await load();
    } catch (error) {
      statusMessage.textContent = error.message;
    }
  });

  document.querySelector('#runReminders').addEventListener('click', async () => {
    try {
      const result = await request('/api/course-participants/reminders/run', {method:'POST'});
      statusMessage.textContent = `Recordatorios: ${result.sent} enviados de ${result.due} pendientes.`;
      await load();
    } catch (error) {
      statusMessage.textContent = error.message;
    }
  });
  document.querySelector('#refresh').addEventListener('click', load);
  document.querySelector('#changeToken').addEventListener('click', () => {
    sessionStorage.removeItem('participants-admin-token');
    sessionStorage.removeItem('participants-admin-credentials');
    load();
  });
  [courseFilter, statusFilter].forEach(element => element.addEventListener('change', load));
  search.addEventListener('search', load);
  search.addEventListener('keydown', event => event.key === 'Enter' && load());
  load();
})();
