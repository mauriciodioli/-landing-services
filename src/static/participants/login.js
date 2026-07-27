(function(){
  'use strict';
  const form = document.getElementById('loginForm');
  const status = document.getElementById('status');
  form.addEventListener('submit', async e => {
    e.preventDefault();
    status.textContent = '';
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const hp = (document.getElementById('hp') && document.getElementById('hp').value) || '';
    try {
      const payloadBody = {email, password, hp};
      // If site uses reCAPTCHA v2/3, an environment-provided site key can be used client-side
      if (window.__RECAPTCHA_SITE_KEY) {
        try {
          const token = await grecaptcha.execute(window.__RECAPTCHA_SITE_KEY, {action: 'login'});
          payloadBody['g-recaptcha-response'] = token;
        } catch (recapErr) {
          // fallthrough — we'll still submit without token
        }
      }
      const res = await fetch('/auth/login', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payloadBody),
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
