// Ayudas del navegador compartidas por las páginas. Sin dependencias.

let dataPromise = null;

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
  return `/character/${encodeURIComponent(name || '')}`;
}

export function charLink(name, cls = '') {
  return `<a href="${charHref(name)}"${cls ? ` class="${cls}"` : ''}>${esc(name)}</a>`;
}

export function $(id) {
  return document.getElementById(id);
}

/** Filas de tabla o mensaje vacío (colspan = columnas). */
export function rowsOrEmpty(list, cols, render, emptyText = 'Sin datos todavía.') {
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
    questionEl.textContent = 'recarga la página';
  }
}

export function showResult(el, ok, message) {
  el.textContent = message;
  el.className = `result ${ok ? 'ok' : 'err'}`;
}
