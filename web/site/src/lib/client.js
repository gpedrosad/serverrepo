// Ayudas del navegador compartidas por las páginas. Sin dependencias.

let dataPromise = null;
let strings = null;

/** Textos del idioma de la página (Base.astro los embebe en #i18n). t('noPk'), t('updated', {t: '…'}). */
export function t(key, vars) {
  if (!strings) {
    try { strings = JSON.parse(document.getElementById('i18n').textContent); } catch { strings = {}; }
  }
  let text = key.split('.').reduce((o, k) => (o == null ? o : o[k]), strings);
  if (text == null) return key;
  if (vars && typeof text === 'string') text = text.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? vars[k] : m));
  return text;
}

export const isEnglish = () => document.documentElement.lang === 'en';

/** Ruta en el idioma de la página: '/top' -> '/en/top' en inglés. */
export function href(path) {
  return isEnglish() ? (path === '/' ? '/en' : '/en' + path) : path;
}

/** Mensaje del servidor (viene en español) traducido si la página está en inglés. */
export function serverText(message) {
  if (!isEnglish() || !message) return message;
  const known = t('server')[message];
  if (known) return known;
  let m = /^Cuenta (\d+) creada\./.exec(message);
  if (m) return `Account ${m[1]} created. Log in with that number and your password in the client.`;
  m = /^Gracias por tu donación \((.+)\)\. Activaremos premium en «(.+)» al confirmar el pago\.$/.exec(message);
  if (m) return `Thanks for your donation (${m[1]}). We'll activate premium on "${m[2]}" once the payment is confirmed.`;
  return message;
}

/** Tiempos relativos del servidor ('hace 4d', 'ahora') en el idioma de la página. */
export function relTime(text) {
  if (!isEnglish() || !text) return text;
  if (text === 'ahora') return 'now';
  const m = /^hace (\d+)([mhd])$/.exec(text);
  return m ? `${m[1]}${m[2]} ago` : text;
}

/** /api/data una sola vez por página (force = volver a pedir, p. ej. el refresco de Live). */
export function getData(force = false) {
  if (!dataPromise || force) {
    dataPromise = fetch('/api/data', { cache: 'no-store' }).then((r) => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
    dataPromise.catch(() => { dataPromise = null; });
  }
  return dataPromise;
}

export function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

export function charHref(name) {
  return href(`/character/${encodeURIComponent(name || '')}`);
}

export function charLink(name, cls = '') {
  return `<a href="${charHref(name)}"${cls ? ` class="${cls}"` : ''}>${esc(name)}</a>`;
}

export function $(id) {
  return document.getElementById(id);
}

/** Filas de tabla o mensaje vacío (colspan = columnas). */
export function rowsOrEmpty(list, cols, render, emptyText = '—') {
  if (!list || !list.length) return `<tr><td colspan="${cols}" class="empty">${esc(emptyText)}</td></tr>`;
  return list.map(render).join('');
}

export function fmtPrice(n) {
  return '$' + Number(n || 0).toLocaleString('es-CL');
}

/** Formulario con captcha del servidor: pide el desafío y marca la hora de apertura. */
export async function loadChallenge(form, questionEl) {
  form.form_ts.value = String(Date.now() / 1000);
  try {
    const r = await fetch('/api/register-challenge', { cache: 'no-store' });
    const d = await r.json();
    form.challenge_id.value = d.id || '';
    questionEl.textContent = d.question || '—';
    form.captcha.value = '';
  } catch {
    questionEl.textContent = t('captchaReload');
  }
}

export function showResult(el, ok, message) {
  el.textContent = serverText(message);
  el.className = `result ${ok ? 'ok' : 'err'}`;
}
