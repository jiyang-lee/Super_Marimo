import { renderSiteNav } from './site-common.js';

document.querySelectorAll('[data-site-nav]').forEach((host) => {
  const active = host.getAttribute('data-active') || 'home';
  host.innerHTML = renderSiteNav(active);
});

