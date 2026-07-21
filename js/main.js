/* =========================================================
   Landing Services — JavaScript principal
   ========================================================= */

(function () {
  'use strict';

  /* ---------- Navbar: toggle móvil ---------- */
  const navToggle = document.getElementById('navToggle');
  const navMenu   = document.getElementById('navMenu');

  if (navToggle && navMenu) {
    navToggle.addEventListener('click', () => {
      const isOpen = navMenu.classList.toggle('is-open');
      navToggle.classList.toggle('is-open', isOpen);
      navToggle.setAttribute('aria-expanded', isOpen);
    });

    /* Cerrar menú al hacer clic en un enlace */
    navMenu.querySelectorAll('.navbar__link').forEach(link => {
      link.addEventListener('click', () => {
        navMenu.classList.remove('is-open');
        navToggle.classList.remove('is-open');
        navToggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* ---------- Navbar: sombra al hacer scroll ---------- */
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    window.addEventListener('scroll', () => {
      navbar.style.boxShadow = window.scrollY > 10
        ? '0 4px 20px rgba(0,0,0,.15)'
        : '';
    }, { passive: true });
  }

  /* ---------- Accordion ---------- */
  document.querySelectorAll('.accordion__btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const item    = btn.closest('.accordion__item');
      const isOpen  = item.classList.contains('is-open');

      /* Cerrar todos */
      document.querySelectorAll('.accordion__item.is-open').forEach(open => {
        open.classList.remove('is-open');
        open.querySelector('.accordion__btn').setAttribute('aria-expanded', 'false');
      });

      /* Abrir el actual (si estaba cerrado) */
      if (!isOpen) {
        item.classList.add('is-open');
        btn.setAttribute('aria-expanded', 'true');
      }
    });
  });

  /* ---------- Formulario de contacto ---------- */
  const contactForm = document.getElementById('contactForm');
  if (contactForm) {
    contactForm.addEventListener('submit', function (e) {
      e.preventDefault();

      const btn         = contactForm.querySelector('[type="submit"]');
      const originalText = btn.textContent;

      btn.disabled    = true;
      btn.textContent = 'Enviando…';

      /* Simulación de envío (reemplazar por fetch real) */
      setTimeout(() => {
        btn.textContent = '¡Mensaje enviado! ✓';
        btn.style.background = '#16a34a';
        contactForm.reset();

        setTimeout(() => {
          btn.disabled    = false;
          btn.textContent = originalText;
          btn.style.background = '';
        }, 4000);
      }, 1200);
    });
  }

  /* ---------- Animación de contador (stats) ---------- */
  function animateCounter(el) {
    const target   = parseInt(el.dataset.target, 10);
    const duration = 1500;
    const step     = target / (duration / 16);
    let   current  = 0;

    const update = () => {
      current = Math.min(current + step, target);
      el.textContent = Math.floor(current) + (el.dataset.suffix || '');
      if (current < target) requestAnimationFrame(update);
    };
    requestAnimationFrame(update);
  }

  /* Observar contadores */
  const counters = document.querySelectorAll('[data-target]');
  if (counters.length && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });

    counters.forEach(c => observer.observe(c));
  }

  /* ---------- Smooth reveal on scroll ---------- */
  const revealEls = document.querySelectorAll(
    '.service-card, .process__step, .service-detail-card, .pricing-card, .timeline__item'
  );

  if (revealEls.length && 'IntersectionObserver' in window) {
    revealEls.forEach(el => {
      el.style.opacity  = '0';
      el.style.transform = 'translateY(20px)';
      el.style.transition = 'opacity .5s ease, transform .5s ease';
    });

    const revealObserver = new IntersectionObserver(entries => {
      entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
          setTimeout(() => {
            entry.target.style.opacity   = '1';
            entry.target.style.transform = 'translateY(0)';
          }, 80 * (i % 4));
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });

    revealEls.forEach(el => revealObserver.observe(el));
  }

  /* ---------- Enlace activo en la nav según scroll ---------- */
  const sections = document.querySelectorAll('section[id]');
  if (sections.length) {
    const links = document.querySelectorAll('.navbar__link[href^="#"]');
    const activateLink = () => {
      let current = '';
      sections.forEach(sec => {
        if (window.scrollY >= sec.offsetTop - 80) current = sec.id;
      });
      links.forEach(link => {
        link.classList.toggle(
          'navbar__link--active',
          link.getAttribute('href') === '#' + current
        );
      });
    };

    window.addEventListener('scroll', activateLink, { passive: true });
    activateLink();
  }

  /* ---------- Año dinámico en el footer ---------- */
  const yearEl = document.getElementById('currentYear');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

})();
