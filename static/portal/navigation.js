(() => {
  const toggle = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('app-sidebar');
  if (toggle && sidebar) toggle.addEventListener('click', () => {
    const open = sidebar.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', String(open));
  });
})();
