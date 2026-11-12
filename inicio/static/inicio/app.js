(() => {
  const sidebar = document.getElementById('app-sidebar');
  const toggle = document.querySelector('.sidebar-toggle');
  const close = document.querySelector('.sidebar-close');
  const backdrop = document.querySelector('.sidebar-backdrop');
  if (!sidebar || !toggle || !close || !backdrop) return;
  const mobile = window.matchMedia('(max-width: 960px)');
  const setOpen = (open, restoreFocus = false) => {
    const expanded = mobile.matches && open;
    document.body.classList.toggle('nav-open', expanded);
    toggle.setAttribute('aria-expanded', String(expanded));
    toggle.setAttribute('aria-label', expanded ? 'Cerrar menú' : 'Abrir menú');
    backdrop.hidden = !expanded;
    sidebar.inert = mobile.matches && !expanded;
    if (expanded) close.focus();
    else if (restoreFocus) toggle.focus();
  };
  toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'));
  close.addEventListener('click', () => setOpen(false, true));
  backdrop.addEventListener('click', () => setOpen(false, true));
  document.addEventListener('keydown', event => {
    if (!mobile.matches || toggle.getAttribute('aria-expanded') !== 'true') return;
    if (event.key === 'Escape') setOpen(false, true);
    if (event.key === 'Tab') {
      const items = [...sidebar.querySelectorAll('a[href], button')].filter(item => item.getClientRects().length);
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  mobile.addEventListener('change', () => setOpen(false));
  setOpen(false);
})();
