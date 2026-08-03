(() => {
  'use strict';
  const menu = document.querySelector('#mobileMenu');
  const scrim = document.querySelector('#scrim');
  const button = document.querySelector('#menuButton');
  const setMenu = (open) => {
    menu?.classList.toggle('open', open);
    scrim?.classList.toggle('open', open);
    menu?.setAttribute('aria-hidden', String(!open));
    button?.setAttribute('aria-expanded', String(open));
    document.body.style.overflow = open ? 'hidden' : '';
  };
  button?.addEventListener('click', () => setMenu(true));
  document.querySelector('#menuClose')?.addEventListener('click', () => setMenu(false));
  scrim?.addEventListener('click', () => setMenu(false));
  menu?.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => setMenu(false)));
  document.addEventListener('keydown', (event) => event.key === 'Escape' && setMenu(false));

  const tabs = [...document.querySelectorAll('[role="tab"]')];
  const activate = (tab) => tabs.forEach((item) => {
    const selected = item === tab;
    item.setAttribute('aria-selected', String(selected));
    item.tabIndex = selected ? 0 : -1;
    const panel = document.querySelector('#panel-' + item.dataset.service);
    if (panel) panel.hidden = !selected;
  });
  tabs.forEach((tab, index) => {
    tab.tabIndex = index ? -1 : 0;
    tab.addEventListener('click', () => activate(tab));
    tab.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      let next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : index + (event.key === 'ArrowRight' ? 1 : -1);
      next = (next + tabs.length) % tabs.length;
      activate(tabs[next]);
      tabs[next].focus();
    });
  });
  document.querySelector('#year').textContent = new Date().getFullYear();
})();
