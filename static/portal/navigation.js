(() => {
  const toggle = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('app-sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  if (toggle && sidebar) {
    const mobileNavigation = () => window.matchMedia('(max-width: 1100px)').matches;
    const closeMenu = (returnFocus = false) => {
      sidebar.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Open navigation');
      if (backdrop) backdrop.hidden = true;
      sidebar.toggleAttribute('inert', mobileNavigation());
      sidebar.setAttribute('aria-hidden', String(mobileNavigation()));
      if (returnFocus) toggle.focus();
    };
    closeMenu();
    toggle.addEventListener('click', () => {
      const open = !sidebar.classList.contains('is-open');
      sidebar.classList.toggle('is-open', open);
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
      if (backdrop) backdrop.hidden = !open;
      sidebar.toggleAttribute('inert', !open && mobileNavigation());
      sidebar.setAttribute('aria-hidden', String(!open && mobileNavigation()));
      if (open) sidebar.querySelector('a')?.focus();
    });
    backdrop?.addEventListener('click', () => closeMenu(true));
    sidebar.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => closeMenu()));
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && sidebar.classList.contains('is-open')) closeMenu(true);
    });
    window.addEventListener('resize', () => closeMenu());
  }

  // Lock ordinary POST forms after their first submission to prevent accidental
  // double taps while the browser is navigating to the response.
  document.querySelectorAll('form[method="post"]:not([data-no-submit-lock])').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (form.dataset.submitting === 'true') {
        event.preventDefault();
        return;
      }
      form.dataset.submitting = 'true';
      form.setAttribute('aria-busy', 'true');
      const button = event.submitter || form.querySelector('button[type="submit"],button:not([type])');
      if (button) {
        button.disabled = true;
        button.textContent = button.dataset.busyLabel || 'Submitting...';
      }
    });
  });
})();
