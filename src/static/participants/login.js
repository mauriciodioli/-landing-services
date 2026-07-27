(function(){
  'use strict';
  const form = document.getElementById('loginForm');
  const status = document.getElementById('status');
  form.addEventListener('submit', async e => {
    e.preventDefault();
    status.textContent = '';
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    try {
      const res = await fetch('/auth/login', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({email, password}),
      });
      const payload = await res.json().catch(()=>({}));
      if (!res.ok) throw new Error(payload.error || 'Error');
      // If server returns a token, store it; otherwise store credentials for Basic auth
      if (payload.token) {
        sessionStorage.setItem('participants-admin-token', payload.token);
      } else {
        sessionStorage.setItem('participants-admin-credentials', JSON.stringify({email, password}));
      }
      // redirect to admin page
      window.location.href = '/admin/participantes';
    } catch (err) {
      status.textContent = err.message || 'Error autenticando';
    }
  });
})();
