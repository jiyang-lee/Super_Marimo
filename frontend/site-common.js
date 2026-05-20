export const PAGES = [
  { href: '/beta-dashboard.html', label: '홈', active: 'home' },
  { href: '/sensor-dashboard.html', label: 'Sensor', active: 'sensor' },
];

export function normalizeBase(value, fallback) {
  const raw = String(value ?? fallback ?? '').trim();
  if (!raw) return '';
  return raw.replace(/\/+$/, '');
}

export function endpoint(base, path) {
  return `${normalizeBase(base)}${path}`;
}

export async function fetchJson(url, init = {}) {
  const response = await fetch(url, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init.headers ?? {}),
    },
  });

  const raw = await response.text();
  const data = raw ? safeParseJson(raw) : null;

  if (!response.ok) {
    const detail =
      data && typeof data === 'object'
        ? String(data.detail ?? data.error ?? response.statusText)
        : raw || response.statusText;
    throw new Error(detail);
  }

  return data;
}

export async function fetchBinary(url, init = {}) {
  const response = await fetch(url, init);
  if (!response.ok) {
    const raw = await response.text();
    throw new Error(raw || response.statusText);
  }
  return response.blob();
}

export function safeParseJson(raw) {
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

export function pretty(value) {
  return JSON.stringify(value, null, 2);
}

export function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

export function renderSiteNav(active = 'home') {
  const items = PAGES.map((page) => {
    const isActive = page.active === active;
    return `
      <a class="site-nav-link ${isActive ? 'active' : ''}" href="${page.href}">
        ${page.label}
      </a>
    `;
  }).join('');

  return `
    <nav class="site-nav">
      <div class="site-brand">
        <strong>Super_Marimo</strong>
        <span>server pages</span>
      </div>
      <div class="site-nav-links">${items}</div>
    </nav>
  `;
}

export function renderStatusStrip(items) {
  return items
    .map(
      (item) => `
        <div class="status-card">
          <div class="status-name">
            <span>${escapeHtml(item.label)}</span>
            <span class="status-dot ${item.ok ? 'ok' : item.ok === false ? 'bad' : 'warn'}"></span>
          </div>
          <div class="status-value">${escapeHtml(item.value ?? '')}</div>
        </div>
      `,
    )
    .join('');
}
