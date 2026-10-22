'use strict';
// Tabs use native buttons and the WAI-ARIA keyboard pattern.
const tabs = [...document.querySelectorAll('[role="tab"]')];
function selectTab(tab, focus = false) {
  tabs.forEach(item => {
    const selected = item === tab;
    item.setAttribute('aria-selected', String(selected));
    item.tabIndex = selected ? 0 : -1;
    document.getElementById(item.getAttribute('aria-controls')).hidden = !selected;
  });
  if (focus) tab.focus();
}
tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => selectTab(tab));
  tab.addEventListener('keydown', event => {
    let next;
    if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
    if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = tabs.length - 1;
    if (next !== undefined) { event.preventDefault(); selectTab(tabs[next], true); }
  });
});
const languageMenu = document.querySelector('.languages');
document.addEventListener('click', event => {
  if (languageMenu && !languageMenu.contains(event.target)) languageMenu.open = false;
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && languageMenu?.open) {
    languageMenu.open = false;
    languageMenu.querySelector('summary').focus();
  }
});
const form = document.getElementById('project-form');
if (form) form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const button = form.querySelector('[type="submit"]');
  const status = document.getElementById('form-status');
  const initial = button.innerHTML;
  const data = new FormData(form);
  const integrationDetails = String(data.get('integration_details') || '').trim();
  const payload = {
    name: data.get('name'), email: data.get('email'), business_type: data.get('business_type'),
    solution_type: data.get('solution_type'), features: data.get('features'),
    online_payments: data.has('online_payments') ? 'yes' : 'no', ai: data.has('ai') ? 'yes' : 'no',
    integration: integrationDetails ? 'yes' : 'unsure',
    description: data.get('description'), integration_details: integrationDetails,
    privacy_consent: data.has('privacy_consent'), website: data.get('website'),
    csrf_token: document.querySelector('meta[name="csrf-token"]').content, lang: form.dataset.lang
  };
  button.disabled = true;
  button.textContent = form.dataset.sending;
  status.textContent = '';
  form.setAttribute('aria-busy', 'true');
  try {
    const response = await fetch('/api/leads', {method:'POST', headers:{'Content-Type':'application/json'}, credentials:'same-origin', body:JSON.stringify(payload)});
    const result = await response.json();
    if (!response.ok || result.ok !== true) throw new Error('submission');
    status.textContent = form.dataset.success;
    status.dataset.state = 'success';
    form.reset();
  } catch (error) {
    status.textContent = error instanceof TypeError ? form.dataset.networkError : form.dataset.error;
    status.dataset.state = 'error';
  } finally {
    button.disabled = false;
    button.innerHTML = initial;
    form.removeAttribute('aria-busy');
  }
});

// Respect reduced motion and data-saving settings; native controls remain available.
const presentationVideo = document.getElementById('presentation-video');
if (presentationVideo && !window.matchMedia('(prefers-reduced-motion: reduce)').matches && !navigator.connection?.saveData) {
  presentationVideo.play().catch(() => {});
}
