(() => {
  'use strict';

  // Introduce aquí la URL completa del endpoint que guardará los registros.
  const REGISTRATION_ENDPOINT = '';

  const form = document.querySelector('#registrationForm');
  const status = document.querySelector('#formStatus');
  const submitButton = form.querySelector('button[type="submit"]');
  const buttonLabel = submitButton.querySelector('.button-label');
  const messages = {valueMissing:'Este campo es obligatorio.',typeMismatch:'Introduce un correo electrónico válido.',tooShort:'Introduce al menos 2 caracteres.'};

  function showFieldError(field) {
    const error = field.closest('label')?.querySelector('.field-error');
    if (!error) return;
    field.classList.toggle('invalid', !field.validity.valid);
    if (field.validity.valid) return void (error.textContent = '');
    const key = Object.keys(messages).find(name => field.validity[name]);
    error.textContent = messages[key] || 'Revisa este campo.';
  }

  form.querySelectorAll('input:not([type="checkbox"]), select').forEach(field => {
    field.addEventListener('blur', () => showFieldError(field));
    field.addEventListener('input', () => field.classList.contains('invalid') && showFieldError(field));
  });

  function tracking() {
    const query = new URLSearchParams(location.search);
    return {utm_source:query.get('utm_source'),utm_medium:query.get('utm_medium'),utm_campaign:query.get('utm_campaign'),utm_content:query.get('utm_content'),utm_term:query.get('utm_term'),referrer:document.referrer||null,page_url:location.href};
  }

  form.addEventListener('submit', async event => {
    event.preventDefault();
    status.className = 'form-status'; status.textContent = '';
    form.querySelectorAll('input:not([type="checkbox"]), select').forEach(showFieldError);
    if (!form.checkValidity()) {
      status.classList.add('error'); status.textContent = 'Revisa los campos indicados antes de continuar.'; form.querySelector(':invalid')?.focus(); return;
    }

    const endpoint = form.dataset.endpoint || REGISTRATION_ENDPOINT;
    const values = Object.fromEntries(new FormData(form).entries());
    const payload = {...values,consent:values.consent==='true',course_slug:form.dataset.courseSlug,course_title:form.dataset.courseTitle,course_date:form.dataset.courseDate||null,course_timezone:form.dataset.courseTimezone||'Europe/Rome',source:'inmersion-ia-procesos',submitted_at:new Date().toISOString(),language:navigator.language,browser_language:navigator.language,screen_resolution:screen.width+'x'+screen.height,...tracking()};
    if (!endpoint) {status.classList.add('error');status.textContent='El formulario está listo. Falta configurar la URL del endpoint en app.js.';return;}

    submitButton.disabled = true; buttonLabel.textContent = 'Enviando solicitud…';
    try {
      const response = await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify(payload)});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      form.reset(); form.querySelectorAll('.field-error').forEach(item => item.textContent='');
      status.classList.add('success'); status.textContent='¡Solicitud recibida! Te enviaremos la información de la próxima edición.';
    } catch (error) {
      console.error('No se pudo enviar la solicitud:',error); status.classList.add('error'); status.textContent='No pudimos enviar tus datos. Inténtalo nuevamente o contacta directamente con el organizador.';
    } finally {submitButton.disabled=false;buttonLabel.textContent='Quiero recibir información';}
  });

  document.querySelector('#year').textContent = new Date().getFullYear();
})();
