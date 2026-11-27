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

/** Idioma de la página: 'es', 'en' o 'pt' (sale del <html lang> que pone Base.astro). */
export function pageLang() {
  const l = (document.documentElement.lang || 'es').slice(0, 2);
  return l === 'en' || l === 'pt' ? l : 'es';
}
export const isEnglish = () => pageLang() === 'en';

/** Ruta en el idioma de la página: '/top' -> '/en/top' o '/pt/top'. */
export function href(path) {
  const l = pageLang();
  if (l === 'es') return path;
  return path === '/' ? '/' + l : '/' + l + path;
}

/** Reglas e info (OTINFO) en el idioma de la página; si falta la traducción, en español. */
export function otinfoFor(d) {
  const l = pageLang();
  const tr = l === 'es' ? null : d['otinfo_' + l];
  return tr && tr.length ? tr : (d.otinfo || []);
}

/** Mensaje del servidor (viene en español) traducido al idioma de la página. */
export function serverText(message) {
  if (pageLang() === 'es' || !message) return message;
  const known = t('server')[message];
  if (known) return known;
  let m = /^Cuenta (\d+) creada\./.exec(message);
  if (m) return t('accountCreated', { n: m[1] });
  m = /^Gracias por tu donación \((.+)\)\. Activaremos premium en «(.+)» al confirmar el pago\.$/.exec(message);
  if (m) return t('donationThanks', { plan: m[1], name: m[2] });
  return message;
}

/** Tiempos relativos del servidor ('hace 4d', 'ahora') en el idioma de la página. */
export function relTime(text) {
  if (pageLang() === 'es' || !text) return text;
  if (text === 'ahora') return t('relNow');
  const m = /^hace (\d+)([mhd])$/.exec(text);
  return m ? t('relAgo', { n: m[1], u: m[2] }) : text;
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
