// Dibujo a RGBA crudo (Uint8Array) en JS; sharp se usa después para codificar, escalar y componer.
import { FLOORCHANGE, OTB_FLAGS, minimapRgb } from './assets.mjs';

export const SCALES = [32, 16, 8, 4, 2, 1];
export const BG = [28, 28, 32];
const MARGIN = 3; // los ítems grandes y con offset se dibujan hacia arriba-izquierda

export class Canvas {
  constructor(w, h, bg = BG) {
    if (w * h > 400e6) throw new Error(`imagen de ${w}x${h} px es demasiado grande: bajá --px`);
    this.w = w; this.h = h;
    this.data = new Uint8Array(w * h * 4);
    const [r, g, b] = bg;
    for (let i = 0; i < this.data.length; i += 4) { this.data[i] = r; this.data[i + 1] = g; this.data[i + 2] = b; this.data[i + 3] = 255; }
  }

  /** Pega un sprite s x s con alfa (0/255 a 32 px, parcial al reducir). */
  blit(spr, s, ox, oy) {
    const { w, h, data } = this;
    const xa = Math.max(0, -ox), xb = Math.min(s, w - ox);
    if (xa >= xb) return;
    for (let yy = Math.max(0, -oy), ye = Math.min(s, h - oy); yy < ye; yy++) {
      let si = (yy * s + xa) * 4, di = ((oy + yy) * w + ox + xa) * 4;
      for (let xx = xa; xx < xb; xx++, si += 4, di += 4) {
        const a = spr[si + 3];
        if (a === 0) continue;
        if (a === 255) { data[di] = spr[si]; data[di + 1] = spr[si + 1]; data[di + 2] = spr[si + 2]; }
        else {
          const ia = 255 - a;
          data[di] = (spr[si] * a + data[di] * ia) / 255;
          data[di + 1] = (spr[si + 1] * a + data[di + 1] * ia) / 255;
          data[di + 2] = (spr[si + 2] * a + data[di + 2] * ia) / 255;
        }
      }
    }
  }

  /** Rectángulo relleno con alfa 0..1. */
  fill(x, y, w, h, [r, g, b], alpha = 1) {
    const x0 = Math.max(0, x), y0 = Math.max(0, y), x1 = Math.min(this.w, x + w), y1 = Math.min(this.h, y + h);
    const a = Math.round(alpha * 255), ia = 255 - a, d = this.data;
    for (let yy = y0; yy < y1; yy++) for (let xx = x0, i = (yy * this.w + x0) * 4; xx < x1; xx++, i += 4) {
      if (a === 255) { d[i] = r; d[i + 1] = g; d[i + 2] = b; }
      else { d[i] = (r * a + d[i] * ia) / 255; d[i + 1] = (g * a + d[i + 1] * ia) / 255; d[i + 2] = (b * a + d[i + 2] * ia) / 255; }
    }
  }

  outline(x, y, w, h, color, t = 1) {
    this.fill(x, y, w, t, color); this.fill(x, y + h - t, w, t, color);
    this.fill(x, y, t, h, color); this.fill(x + w - t, y, t, h, color);
  }

  /** Copia otro Canvas (o RGBA crudo) en (ox, oy). */
  paste(src, sw, sh, ox, oy) {
    for (let y = 0; y < sh; y++) {
      const Y = oy + y;
      if (Y < 0 || Y >= this.h) continue;
      const xa = Math.max(0, -ox), xb = Math.min(sw, this.w - ox);
      if (xa >= xb) continue;
      this.data.set(src.subarray((y * sw + xa) * 4, (y * sw + xb) * 4), (Y * this.w + ox + xa) * 4);
    }
  }
}

/** Ítems de la casilla en orden de dibujo (ground, borde, bottom, común, top; estable). */
function drawList(assets, items) {
  const list = [];
  for (const sid of items) { const e = assets.entries.get(sid); if (e) list.push(e); }
  if (list.length > 1) list.sort((a, b) => a.rank - b.rank);
  return list;
}

/** Dibuja un piso con sprites. `shift` = pisos de arriba vistos desde abajo (corridos arriba-izquierda). */
function drawFloor(cv, assets, map, x0, y0, x1, y1, z, s, shift = 0) {
  const k = s / 32;
  for (const t of map.region(x0, y0, x1 + MARGIN + shift, y1 + MARGIN + shift, z)) {
    const bx = (t.x - x0 - shift) * s, by = (t.y - y0 - shift) * s;
    let elev = 0;
    for (const e of drawList(assets, t.items)) {
      const xp = t.x % e.px, yp = t.y % e.py;
      for (let hy = 0; hy < e.h; hy++) for (let wx = 0; wx < e.w; wx++) for (let L = 0; L < e.layers; L++) {
        const idx = ((yp * e.px + xp) * e.layers + L) * e.h * e.w + hy * e.w + wx;
        if (idx >= e.sprites.length) continue;
        const spr = assets.spr.get(e.sprites[idx], s);
        if (!spr) continue;
        cv.blit(spr, s, bx - Math.round((wx * 32 + e.dx + elev) * k), by - Math.round((hy * 32 + e.dy + elev) * k));
      }
      if (e.elev) elev = Math.min(24, elev + e.elev);
    }
  }
}

/** Render de región con sprites reales. px por casilla ∈ {32,16,8,4,2,1}; above = pisos de arriba (techos). */
export function renderRegion(assets, map, { x0, y0, x1, y1, z, px = 32, above = 0 }) {
  if (!SCALES.includes(px)) throw new Error(`--px debe ser uno de ${SCALES.join(', ')} (para otros tamaños usá --width)`);
  const cv = new Canvas((x1 - x0 + 1) * px, (y1 - y0 + 1) * px);
  for (let k = 0; k <= above; k++) if (z - k >= 0) drawFloor(cv, assets, map, x0, y0, x1, y1, z - k, px, k);
  return cv;
}

// ---------------------------------------------------------------- minimapa y capas (1 casilla = px)
/** Minimapa: color de minimapa del .dat del ítem más alto que tenga uno (como el cliente). */
export function renderMinimap(assets, map, { x0, y0, x1, y1, z, px = 1 }) {
  const cv = new Canvas((x1 - x0 + 1) * px, (y1 - y0 + 1) * px, [0, 0, 0]);
  for (const t of map.region(x0, y0, x1, y1, z)) {
    let c = -1;
    for (const e of drawList(assets, t.items)) if (e.minimap >= 0) c = e.minimap;
    if (c >= 0) cv.fill((t.x - x0) * px, (t.y - y0) * px, px, px, minimapRgb(c));
  }
  return cv;
}

export const WALK = {
  void: { color: [0, 0, 0], ch: ' ' },
  walk: { color: [70, 160, 70], ch: '.' },
  pz: { color: [150, 215, 150], ch: ',' },
  block: { color: [120, 40, 40], ch: '#' },
  water: { color: [30, 50, 120], ch: '~' },
  field: { color: [230, 150, 40], ch: '*' },
  stairs: { color: [60, 140, 255], ch: '>' },
  teleport: { color: [230, 60, 230], ch: 'T' },
};

/** Clase de transitabilidad de una casilla (por flags del OTB, como el servidor). */
export function walkClass(assets, t) {
  if (!t || !t.items.length) return 'void';
  let ground = false, block = false, groundBlock = false, stairs = false, tp = false, field = false;
  for (const sid of t.items) {
    const e = assets.entries.get(sid);
    if (!e) continue;
    if (e.rank === 0) { ground = true; if (e.otbFlags & OTB_FLAGS.block_solid) groundBlock = true; }
    else if (e.otbFlags & OTB_FLAGS.block_solid) block = true;
    if ((e.otbFlags & FLOORCHANGE) || e.floorChange) stairs = true;
    if (e.group === 'teleport') tp = true;
    if (e.group === 'magicfield') field = true;
  }
  if (tp) return 'teleport';
  if (stairs) return 'stairs';
  if (!ground) return 'void';
  if (block) return 'block';
  if (groundBlock) return 'water'; // suelo que no se pisa: agua, lava, abismo
  if (field) return 'field';
  return (t.flags & 1) ? 'pz' : 'walk';
}

export function renderWalk(assets, map, { x0, y0, x1, y1, z, px = 1 }, counts = {}) {
  const cv = new Canvas((x1 - x0 + 1) * px, (y1 - y0 + 1) * px, WALK.void.color);
  for (const t of map.region(x0, y0, x1, y1, z)) {
    const c = walkClass(assets, t);
    counts[c] = (counts[c] || 0) + 1;
    if (c !== 'void') cv.fill((t.x - x0) * px, (t.y - y0) * px, px, px, WALK[c].color);
  }
  return cv;
}

/** Texto: un carácter por casilla, con regla de coordenadas cada 10. Lo más barato para un modelo. */
export function asciiWalk(assets, map, { x0, y0, x1, y1, z }) {
  const W = x1 - x0 + 1;
  const rows = [];
  let head = '      ';
  for (let x = x0; x <= x1; x++) head += x % 10 === 0 ? '|' : ' ';
  rows.push(`z${z} x${x0}..${x1} y${y0}..${y1}  (| = x múltiplo de 10)`);
  rows.push(head);
  for (let y = y0; y <= y1; y++) {
    const line = new Array(W).fill(' ');
    for (const t of map.region(x0, y, x1, y, z)) line[t.x - x0] = WALK[walkClass(assets, t)].ch;
    rows.push(`${String(y).padStart(5)} ${line.join('').trimEnd()}`);
  }
  rows.push(`leyenda: ${Object.entries(WALK).map(([k, v]) => `'${v.ch}'=${k}`).join(' ')}`);
  return rows.join('\n');
}

// ---------------------------------------------------------------- densidad
/** Grilla de conteo por casilla: ítems no-suelo o monstruos de test-spawn.xml. */
export function densityGrid(assets, map, spawns, { x0, y0, x1, y1, z, what = 'monsters' }) {
  const W = x1 - x0 + 1, H = y1 - y0 + 1, g = new Float32Array(W * H);
  if (what === 'monsters') {
    for (const s of spawns) {
      if (s.kind === 'monster' && s.z === z && s.x >= x0 && s.x <= x1 && s.y >= y0 && s.y <= y1) g[(s.y - y0) * W + s.x - x0]++;
    }
  } else {
    for (const t of map.region(x0, y0, x1, y1, z)) {
      let n = 0;
      for (const sid of t.items) { const e = assets.entries.get(sid); if (e && e.rank !== 0 && e.rank !== 1) n++; }
      g[(t.y - y0) * W + t.x - x0] = n;
    }
  }
  return { W, H, g };
}

/** Suma por ventana cuadrada (radio r) para que la densidad sea "por zona" y no por casilla. */
export function boxBlur({ W, H, g }, r) {
  if (r <= 0) return { W, H, g };
  const ii = new Float64Array((W + 1) * (H + 1));
  for (let y = 0; y < H; y++) for (let x = 0, row = 0; x < W; x++) {
    row += g[y * W + x];
    ii[(y + 1) * (W + 1) + x + 1] = ii[y * (W + 1) + x + 1] + row;
  }
  const out = new Float32Array(W * H);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const xa = Math.max(0, x - r), xb = Math.min(W, x + r + 1), ya = Math.max(0, y - r), yb = Math.min(H, y + r + 1);
    out[y * W + x] = ii[yb * (W + 1) + xb] - ii[ya * (W + 1) + xb] - ii[yb * (W + 1) + xa] + ii[ya * (W + 1) + xa];
  }
  return { W, H, g: out };
}

/** Paleta tipo "inferno" simplificada para el mapa de calor (0..1). */
export function heat(v) {
  const stops = [[0, [0, 0, 4]], [0.25, [87, 16, 110]], [0.5, [188, 55, 84]], [0.75, [249, 142, 9]], [1, [252, 255, 164]]];
  v = Math.max(0, Math.min(1, v));
  for (let i = 1; i < stops.length; i++) {
    if (v <= stops[i][0]) {
      const [a, ca] = stops[i - 1], [b, cb] = stops[i], f = (v - a) / (b - a);
      return ca.map((c, k) => Math.round(c + (cb[k] - c) * f));
    }
  }
  return stops[stops.length - 1][1];
}

// ---------------------------------------------------------------- diff entre dos mapas
const same = (a, b) => a && b && a.sig === b.sig;

/** Casillas distintas en el rectángulo: [{x, y, z, kind: 'added'|'removed'|'changed'}]. */
export function diffTiles(base, cur, { x0, y0, x1, y1, z }) {
  const out = [];
  const seen = new Set();
  for (const t of cur.region(x0, y0, x1, y1, z)) {
    const b = base.get(t.x, t.y, z);
    seen.add(t.y * 65536 + t.x);
    if (!b || !b.items.length) { if (t.items.length) out.push({ x: t.x, y: t.y, z, kind: 'added' }); }
    else if (!same(b, t)) out.push({ x: t.x, y: t.y, z, kind: 'changed' });
  }
  for (const b of base.region(x0, y0, x1, y1, z)) {
    if (!seen.has(b.y * 65536 + b.x) && b.items.length) out.push({ x: b.x, y: b.y, z, kind: 'removed' });
  }
  return out;
}

export const DIFF_COLORS = { added: [40, 220, 90], removed: [240, 50, 50], changed: [255, 210, 0] };

/** Agrupa cambios en zonas (bloques de 8x8 casillas conectados) para resumir en texto. */
export function clusters(diffs, block = 8) {
  const cells = new Map();
  for (const d of diffs) {
    const k = `${Math.floor(d.x / block)},${Math.floor(d.y / block)}`;
    let c = cells.get(k);
    if (!c) cells.set(k, (c = []));
    c.push(d);
  }
  const done = new Set(), out = [];
  for (const k of cells.keys()) {
    if (done.has(k)) continue;
    const stack = [k], group = [];
    done.add(k);
    while (stack.length) {
      const cur = stack.pop();
      group.push(...cells.get(cur));
      const [cx, cy] = cur.split(',').map(Number);
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        const n = `${cx + dx},${cy + dy}`;
        if (cells.has(n) && !done.has(n)) { done.add(n); stack.push(n); }
      }
    }
    const xs = group.map((d) => d.x), ys = group.map((d) => d.y);
    const kinds = {};
    for (const d of group) kinds[d.kind] = (kinds[d.kind] || 0) + 1;
    out.push({ bbox: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)], tiles: group.length, ...kinds });
  }
  return out.sort((a, b) => b.tiles - a.tiles);
}
