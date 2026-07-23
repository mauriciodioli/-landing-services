(() => {
  'use strict';

  // Pegá aquí la URL del endpoint que guardará los registros.
  const REGISTRATION_ENDPOINT = '';

  const form = document.querySelector('#registrationForm');
  const status = document.querySelector('#formStatus');
  const button = form.querySelector('button[type="submit"]');
  const buttonLabel = button.querySelector('.button-label');
  const messages = {valueMissing:'Este campo es obligatorio.',typeMismatch:'Ingresá un correo electrónico válido.',tooShort:'Ingresá al menos 2 caracteres.'};

  function validate(field) {
    const error = field.closest('label')?.querySelector('.field-error');
    if (!error) return;
    field.classList.toggle('invalid', !field.validity.valid);
    if (field.validity.valid) return void (error.textContent = '');
    const key = Object.keys(messages).find(item => field.validity[item]);
    error.textContent = messages[key] || 'Revisá este campo.';
  }

  form.querySelectorAll('input:not([type="checkbox"]),select').forEach(field => {
    field.addEventListener('blur', () => validate(field));
    field.addEventListener('input', () => field.classList.contains('invalid') && validate(field));
  });

  form.addEventListener('submit', async event => {
    event.preventDefault();
    status.className = 'form-status'; status.textContent = '';
    form.querySelectorAll('input:not([type="checkbox"]),select').forEach(validate);
    if (!form.checkValidity()) {status.classList.add('error');status.textContent='Revisá los campos indicados.';form.querySelector(':invalid')?.focus();return;}

    const params = new URLSearchParams(location.search);
    const values = Object.fromEntries(new FormData(form).entries());
    const payload = {...values,consent:values.consent==='true',course_slug:form.dataset.courseSlug,course_title:form.dataset.courseTitle,course_date:form.dataset.courseDate||null,course_timezone:form.dataset.courseTimezone||'Europe/Rome',source:'landing-ia-marketing',submitted_at:new Date().toISOString(),utm_source:params.get('utm_source'),utm_medium:params.get('utm_medium'),utm_campaign:params.get('utm_campaign'),utm_term:params.get('utm_term'),utm_content:params.get('utm_content'),referrer:document.referrer||null,page_url:location.href,language:navigator.language,browser_language:navigator.language,screen_resolution:screen.width+'x'+screen.height};
    const endpoint = form.dataset.endpoint || REGISTRATION_ENDPOINT;
    if (!endpoint) {status.classList.add('error');status.textContent='El formulario está listo. Falta configurar el endpoint en app.js.';return;}

    button.disabled=true;buttonLabel.textContent='Enviando…';
    try {
      const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify(payload)});
      if(!response.ok) throw new Error(`HTTP ${response.status}`);
      form.reset();form.querySelectorAll('.field-error').forEach(item=>item.textContent='');status.classList.add('success');status.textContent='¡Gracias! Te enviaremos la información de la próxima edición.';
    } catch(error) {console.error('Error al enviar el formulario:',error);status.classList.add('error');status.textContent='No pudimos enviar tus datos. Intentá nuevamente.';}
    finally {button.disabled=false;buttonLabel.textContent='Quiero recibir información';}
  });

  document.querySelector('#year').textContent=new Date().getFullYear();
})();
