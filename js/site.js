/* Haven 2.0 — gemensam navigering och automatiskt årtal.
   Inga bibliotek behövs. Laddas med defer på alla V2-sidor.
*/
(() => {
  'use strict';

  const yearElement = document.getElementById('year');
  if (yearElement) {
    yearElement.textContent = String(new Date().getFullYear());
  }

  const toggle = document.querySelector('.v2-menu-toggle');
  const nav = document.getElementById('v2-main-navigation');
  if (!toggle || !nav) return;

  const groups = [...nav.querySelectorAll('details.v2-nav-group')];
  const mobile = window.matchMedia('(max-width: 920px)');

  function closeMenu() {
    nav.classList.remove('is-open');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', 'Öppna menyn');
    groups.forEach(group => { group.open = false; });
  }

  toggle.addEventListener('click', () => {
    const isOpen = nav.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', String(isOpen));
    toggle.setAttribute('aria-label', isOpen ? 'Stäng menyn' : 'Öppna menyn');
    if (!isOpen) groups.forEach(group => { group.open = false; });
  });

  groups.forEach(group => {
    group.addEventListener('toggle', () => {
      if (group.open) groups.filter(item => item !== group).forEach(item => { item.open = false; });
    });
  });

  document.addEventListener('click', event => {
    if (!event.target.closest('.v2-site-header')) closeMenu();
  });

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      const wasOpen = nav.classList.contains('is-open');
      closeMenu();
      if (wasOpen) toggle.focus();
    }
  });

  nav.addEventListener('click', event => {
    if (mobile.matches && event.target.closest('a')) closeMenu();
  });

  mobile.addEventListener('change', closeMenu);
})();
