// Todo lo que pasa por sharp/libvips: codificar, escalar, rotular con SVG y armar grillas.
import sharp from 'sharp';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { Canvas } from './render.mjs';

sharp.cache(false);

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export function fromCanvas(cv) {
  return sharp(cv.data, { raw: { width: cv.w, height: cv.h, channels: 4 } });
}

/** Líneas de grilla cada `n` casillas (alineadas a coordenadas múltiplos de n) + reglas con números. */
export async function withGrid(cv, { x0, y0, px, n = 10 }) {
  const W = cv.w, H = cv.h, tilesW = W / px, tilesH = H / px;
  for (let x = Math.ceil(x0 / n) * n; x < x0 + tilesW; x += n) cv.fill((x - x0) * px, 0, 1, H, [255, 255, 255], 0.35);
  for (let y = Math.ceil(y0 / n) * n; y < y0 + tilesH; y += n) cv.fill(0, (y - y0) * px, W, 1, [255, 255, 255], 0.35);
  const L = 30, T = 13;
  const out = new Canvas(W + L, H + T, [16, 16, 18]);
  out.paste(cv.data, W, H, L, T);
  const texts = [];
  for (let x = Math.ceil(x0 / n) * n; x < x0 + tilesW; x += n) texts.push(`<text x="${L + (x - x0) * px + 1}" y="10">${x}</text>`);
  for (let y = Math.ceil(y0 / n) * n; y < y0 + tilesH; y += n) texts.push(`<text x="1" y="${T + (y - y0) * px + 9}">${y}</text>`);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W + L}" height="${H + T}"><g font-family="Menlo, DejaVu Sans Mono, monospace" font-size="10" fill="#e8e8e8">${texts.join('')}</g></svg>`;
  const raw = await fromCanvas(out).composite([{ input: Buffer.from(svg), top: 0, left: 0 }]).raw().toBuffer();
  const res = new Canvas(1, 1);
  res.w = W + L; res.h = H + T; res.data = new Uint8Array(raw.buffer, raw.byteOffset, raw.length);
  return res;
}

/** Panel con título arriba (para comparar variantes). */
export async function titled(cv, title, h = 18) {
  const out = new Canvas(cv.w, cv.h + h, [16, 16, 18]);
  out.paste(cv.data, cv.w, cv.h, 0, h);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${cv.w}" height="${h}"><text x="4" y="${h - 5}" font-family="Helvetica, Arial, sans-serif" font-size="13" font-weight="bold" fill="#ffd34d">${esc(title)}</text></svg>`;
  const raw = await fromCanvas(out).composite([{ input: Buffer.from(svg), top: 0, left: 0 }]).raw().toBuffer();
  const res = new Canvas(1, 1);
  res.w = out.w; res.h = out.h; res.data = new Uint8Array(raw.buffer, raw.byteOffset, raw.length);
  return res;
}

/** Grilla de paneles del mismo tamaño o no (se alinean arriba-izquierda), con separación. */
export function gridOf(panels, cols, gap = 6) {
  cols = Math.max(1, Math.min(cols || Math.ceil(Math.sqrt(panels.length)), panels.length));
  const rows = Math.ceil(panels.length / cols);
  const cw = Math.max(...panels.map((p) => p.w)), ch = Math.max(...panels.map((p) => p.h));
  const out = new Canvas(cols * cw + (cols - 1) * gap, rows * ch + (rows - 1) * gap, [8, 8, 10]);
  panels.forEach((p, i) => out.paste(p.data, p.w, p.h, (i % cols) * (cw + gap), Math.floor(i / cols) * (ch + gap)));
  return out;
}

/** Imagen cualquiera (png/jpg/webp) -> Canvas RGBA. */
export async function loadImage(path) {
  const { data, info } = await sharp(path).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  const cv = new Canvas(1, 1);
  cv.w = info.width; cv.h = info.height; cv.data = new Uint8Array(data.buffer, data.byteOffset, data.length);
  return cv;
}

/**
 * Codifica y guarda. format: png | webp | jpeg | avif (o por extensión de `out`).
 * width / maxSide: reescala con sharp (vecino más cercano si agranda x2, x3...; mitchell si achica).
 */
export async function encode(cv, { out, format, quality = 80, width, maxSide, lossless = false } = {}) {
  format = format || (out ? (out.split('.').pop().toLowerCase().replace('jpg', 'jpeg')) : 'png');
  let img = fromCanvas(cv);
  let tw = cv.w, th = cv.h;
  if (width && width !== cv.w) { tw = width; th = Math.max(1, Math.round(cv.h * width / cv.w)); }
  if (maxSide && Math.max(tw, th) > maxSide) { const f = maxSide / Math.max(tw, th); tw = Math.max(1, Math.round(tw * f)); th = Math.max(1, Math.round(th * f)); }
  if (tw !== cv.w || th !== cv.h) {
    const up = tw > cv.w && tw % cv.w === 0;
    img = img.resize(tw, th, { kernel: up ? 'nearest' : 'mitchell', fit: 'fill' });
  }
  if (format === 'png') img = img.png({ compressionLevel: 6, adaptiveFiltering: false });
  else if (format === 'webp') img = img.webp(lossless ? { lossless: true } : { quality, effort: 4 });
  else if (format === 'jpeg') img = img.flatten({ background: '#000' }).jpeg({ quality, mozjpeg: true });
  else if (format === 'avif') img = img.avif({ quality, effort: 2 });
  else throw new Error(`formato desconocido: ${format}`);
  const buf = await img.toBuffer();
  if (out) { mkdirSync(dirname(out), { recursive: true }); writeFileSync(out, buf); }
  return { buf, w: tw, h: th, bytes: buf.length, format };
}
