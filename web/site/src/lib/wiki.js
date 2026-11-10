// Wiki de Retro76: artículos en src/wiki/<slug>.md (ver src/wiki/_GUIA.md).
// Se leen y convierten a HTML al compilar; las páginas quedan como HTML puro, sin JS.
// El Markdown es un subconjunto chico a propósito (lo que usa la guía), más tres extras:
//   [[slug]] / [[slug|texto]]  enlace a otro artículo
//   {item:2154}                ícono del ítem (web/assets/wiki/items/2154.png; los genera
//                              scripts/web/build-wiki-icons.py y deja la lista en src/wiki/_icons.json)
//   > **Ojo:** / > **Tip:**    aviso con color

export const CATEGORIES = [
  'Primeros pasos',
  'Progresión y botín',
  'Items especiales',
  'Lugares y actividades',
  'Hechizos y combate',
  'PvP',
  'NPCs y economía',
  'Monstruos',
];

import ICONS from '../wiki/_icons.json';

const RAW = import.meta.glob('../wiki/*.md', { query: '?raw', import: 'default', eager: true });
const HAVE_ICON = new Set(ICONS);

export const hasIcon = (id) => HAVE_ICON.has(Number(id));
export const iconSrc = (id) => `/assets/wiki/items/${id}.png`;

function parseFrontmatter(text, file) {
  const m = text.match(/^---\n([\s\S]*?)\n---\n?/);
  if (!m) throw new Error(`wiki: ${file} no tiene encabezado ---`);
  const meta = {};
  for (const line of m[1].split('\n')) {
    const i = line.indexOf(':');
    if (i > 0) meta[line.slice(0, i).trim()] = line.slice(i + 1).trim();
  }
  return { meta, body: text.slice(m[0].length) };
}

let cache;
/** Todos los artículos publicados, ordenados por categoría y orden. */
export function articles() {
  if (cache) return cache;
  const list = [];
  for (const [path, text] of Object.entries(RAW)) {
    const file = path.split('/').pop();
    if (file.startsWith('_')) continue;
    const slug = file.replace(/\.md$/, '');
    const { meta, body } = parseFrontmatter(text.replace(/\r\n/g, '\n'), file);
    if ((meta.estado || 'publicado') !== 'publicado') continue;
    for (const key of ['titulo', 'categoria', 'resumen']) {
      if (!meta[key]) throw new Error(`wiki: ${file} no tiene "${key}"`);
    }
    if (!CATEGORIES.includes(meta.categoria)) throw new Error(`wiki: ${file} categoría desconocida "${meta.categoria}"`);
    list.push({
      slug,
      title: meta.titulo,
      category: meta.categoria,
      summary: meta.resumen,
      order: Number(meta.orden || 100),
      icon: meta.icono && hasIcon(meta.icono) ? Number(meta.icono) : null,
      body,
    });
  }
  list.sort((a, b) => CATEGORIES.indexOf(a.category) - CATEGORIES.indexOf(b.category) || a.order - b.order || a.title.localeCompare(b.title, 'es'));
  cache = list;
  return list;
}

export function bySlug(slug) {
  return articles().find((a) => a.slug === slug);
}

/** Artículos agrupados por categoría, en el orden de CATEGORIES (sin categorías vacías). */
export function grouped() {
  return CATEGORIES.map((name) => ({ name, items: articles().filter((a) => a.category === name) })).filter((g) => g.items.length);
}

// ---------------------------------------------------------------- Markdown

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

export function slugify(text) {
  return text.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function inline(src, ctx) {
  // El código (`hi`) se aparta primero para no tocar lo que va adentro, y se vuelve a poner al final
  // (así **`!pz`** queda en negrita).
  const codes = [];
  let s = esc(src.replace(/`([^`]+)`/g, (_, c) => `\u0001${codes.push(c) - 1}\u0001`));
  s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (_, alt, url) => `<img src="${url}" alt="${alt}" loading="lazy">`);
  s = s.replace(/\[\[([a-z0-9-]+)(?:\|([^\]]+))?\]\]/g, (_, slug, text) => {
    const target = bySlug(slug);
    const label = text || (target ? target.title : slug);
    if (!target) { ctx.missing.add(slug); return label; }
    return `<a href="/wiki/${slug}">${label}</a>`;
  });
  s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, text, url) => {
    const ext = /^https?:/.test(url) && !url.startsWith('https://retro76.cl');
    return `<a href="${url}"${ext ? ' rel="noopener" target="_blank"' : ''}>${text}</a>`;
  });
  s = s.replace(/\{item:(\d+)\}\s?/g, (_, id) => (hasIcon(id)
    ? `<img class="item-icon" src="${iconSrc(id)}" alt="" width="24" height="24" loading="lazy"> ` : ''));
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*\w])\*([^*\s][^*]*)\*(?!\w)/g, '$1<em>$2</em>');
  return s.replace(/\u0001(\d+)\u0001/g, (_, n) => `<code class="say">${esc(codes[Number(n)])}</code>`);
}

/** Viñeta que es solo un enlace a un artículo que no existe o es borrador: se omite. */
const deadLinkItem = (t) => {
  const m = t.trim().match(/^\[\[([a-z0-9-]+)(?:\|[^\]]+)?\]\]\.?$/);
  return m && !bySlug(m[1]);
};

function splitRow(line) {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
}

function table(lines, ctx) {
  const head = splitRow(lines[0]);
  const aligns = splitRow(lines[1]).map((c) => (c.endsWith(':') && !c.startsWith(':') ? 'n' : ''));
  const rows = lines.slice(2).map(splitRow);
  const cell = (tag, c, i) => `<${tag}${aligns[i] ? ' class="n"' : ''}>${inline(c, ctx)}</${tag}>`;
  return `<div class="table-scroll"><table><thead><tr>${head.map((c, i) => cell('th', c, i)).join('')}</tr></thead>`
    + `<tbody>${rows.map((r) => `<tr>${r.map((c, i) => cell('td', c, i)).join('')}</tr>`).join('')}</tbody></table></div>`;
}

function callout(lines, ctx) {
  const text = lines.map((l) => l.replace(/^>\s?/, '')).join(' ').trim();
  const kind = /^\*\*Ojo:?\*\*/i.test(text) ? 'warn' : /^\*\*Tip:?\*\*/i.test(text) ? 'tip' : 'plain';
  return `<p class="callout ${kind}">${inline(text, ctx)}</p>`;
}

/**
 * Markdown -> { html, toc, missing }. toc = [{id, text}] de los títulos ##.
 * La sección "Lo esencial" queda envuelta en <div class="essentials">.
 */
export function render(md) {
  const ctx = { missing: new Set() };
  const lines = md.split('\n');
  const out = [];
  const toc = [];
  let inEssentials = false;
  let i = 0;
  const closeEssentials = () => { if (inEssentials) { out.push('</div>'); inEssentials = false; } };

  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }

    let m;
    if ((m = line.match(/^(#{2,3})\s+(.*)$/))) {
      const level = m[1].length;
      const text = m[2].trim();
      const id = slugify(text);
      if (level === 2) {
        closeEssentials();
        toc.push({ id, text });
        if (/^lo esencial$/i.test(text)) {
          out.push(`<div class="essentials"><h2 id="${id}">${inline(text, ctx)}</h2>`);
          inEssentials = true;
        } else {
          out.push(`<h2 id="${id}">${inline(text, ctx)}</h2>`);
        }
      } else {
        out.push(`<h3 id="${id}">${inline(text, ctx)}</h3>`);
      }
      i++;
      continue;
    }

    if (line.startsWith('|') && lines[i + 1] && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
      const block = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) block.push(lines[i++]);
      out.push(table(block, ctx));
      continue;
    }

    if (line.startsWith('>')) {
      const block = [];
      while (i < lines.length && lines[i].startsWith('>')) block.push(lines[i++]);
      out.push(callout(block, ctx));
      continue;
    }

    if (/^\s*[-*]\s+/.test(line) || /^\s*\d+[.)]\s+/.test(line)) {
      const ordered = /^\s*\d+[.)]\s+/.test(line);
      const re = ordered ? /^\s*\d+[.)]\s+/ : /^\s*[-*]\s+/;
      const items = [];
      while (i < lines.length && lines[i].trim()) {
        if (re.test(lines[i])) items.push(lines[i].replace(re, ''));
        else if (/^\s+\S/.test(lines[i]) && items.length) items[items.length - 1] += ' ' + lines[i].trim();
        else break;
        i++;
      }
      const tag = ordered ? 'ol' : 'ul';
      const shown = items.filter((t) => !deadLinkItem(t));
      if (shown.length) out.push(`<${tag}>${shown.map((t) => `<li>${inline(t, ctx)}</li>`).join('')}</${tag}>`);
      continue;
    }

    if (/^-{3,}\s*$/.test(line)) { out.push('<hr>'); i++; continue; }

    const para = [];
    while (i < lines.length && lines[i].trim() && !/^(#{2,3}\s|>|\||\s*[-*]\s+|\s*\d+[.)]\s+)/.test(lines[i])) {
      para.push(lines[i++].trim());
    }
    if (!para.length) { para.push(line.trim()); i++; }
    const text = para.join(' ');
    if (/^!\[[^\]]*\]\([^)]+\)$/.test(text)) out.push(`<figure>${inline(text, ctx)}</figure>`);
    else out.push(`<p>${inline(text, ctx)}</p>`);
  }
  closeEssentials();
  return { html: out.join('\n'), toc, missing: [...ctx.missing] };
}

/** Texto plano para el buscador del índice (título, resumen y títulos de sección). */
export function searchText(a) {
  const heads = [...a.body.matchAll(/^#{2,3}\s+(.*)$/gm)].map((m) => m[1]);
  return [a.title, a.summary, a.category, ...heads].join(' ').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}
