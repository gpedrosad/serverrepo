// Lectura de items OTB, Tibia.dat, Tibia.spr (7.6), test.otbm y test-spawn.xml.
// Port a JS de scripts/map/kb/mapdata.py y scripts/map/game_render.py (mismo orden de dibujo,
// offsets 0x18 y elevación 0x19). Sin dependencias: sharp solo se usa para codificar/componer.
import { readFileSync, statSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { dirname, resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

export const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..');
export const PATHS = {
  map: `${REPO}/server/YurOTS/ots/data/world/test.otbm`,
  spawn: `${REPO}/server/YurOTS/ots/data/world/test-spawn.xml`,
  otb: `${REPO}/server/YurOTS/ots/data/items/items-zagan-test.otb`,
  dat: `${REPO}/devtools/rme/rme-client-760/Tibia.dat`,
  spr: `${REPO}/devtools/rme/rme-client-760/Tibia.spr`,
};

const NODE_START = 0xfe, NODE_END = 0xff, ESC = 0xfd;
const T_AREA = 4, T_TILE = 5, T_ITEM = 6, T_HOUSETILE = 14;

export const OTB_FLAGS = {
  block_solid: 1, block_projectile: 2, block_pathfind: 4, has_height: 8, useable: 16,
  pickupable: 32, moveable: 64, stackable: 128, floorchange_down: 256, floorchange_north: 512,
  floorchange_east: 1024, floorchange_south: 2048, floorchange_west: 4096, always_on_top: 8192,
};
export const FLOORCHANGE = 256 | 512 | 1024 | 2048 | 4096;
const OTB_GROUPS = ['none', 'ground', 'container', 'weapon', 'ammunition', 'armor', 'rune',
  'teleport', 'magicfield', 'writeable', 'key', 'splash', 'fluid'];
const DAT_ARGS = { 0x00: 2, 0x08: 2, 0x09: 2, 0x15: 4, 0x18: 4, 0x19: 2, 0x1c: 2, 0x1d: 2 };
// rango de dibujo dentro de una casilla (igual que mapdata.LAYER_RANK)
const RANK_GROUND = 0, RANK_BORDER = 1, RANK_BOTTOM = 2, RANK_COMMON = 3, RANK_TOP = 4;

/** Árbol OTBM/OTB: {type, props: Uint8Array (sin escapes), children}. Iterativo. */
export function parseTree(data) {
  let pos = 4;
  if (data[pos] !== NODE_START) throw new Error('no es un árbol OTB/OTBM');
  const mk = (type) => ({ type, props: null, children: [], _buf: [] });
  const root = mk(data[pos + 1]);
  pos += 2;
  const stack = [root];
  // props: se acumulan por tramos para no copiar byte a byte cuando no hay escapes
  let segStart = pos;
  const flush = (node, end) => {
    if (end > segStart) node._buf.push(data.subarray(segStart, end));
  };
  const close = (node) => {
    const parts = node._buf;
    if (parts.length === 1) node.props = parts[0];
    else {
      let n = 0;
      for (const p of parts) n += p.length;
      const out = new Uint8Array(n);
      let o = 0;
      for (const p of parts) { out.set(p, o); o += p.length; }
      node.props = out;
    }
    delete node._buf;
  };
  const n = data.length;
  while (pos < n && stack.length) {
    const b = data[pos];
    if (b === ESC) {
      const top = stack[stack.length - 1];
      flush(top, pos);
      top._buf.push(data.subarray(pos + 1, pos + 2));
      pos += 2;
      segStart = pos;
    } else if (b === NODE_START) {
      const top = stack[stack.length - 1];
      flush(top, pos);
      const node = mk(data[pos + 1]);
      top.children.push(node);
      stack.push(node);
      pos += 2;
      segStart = pos;
    } else if (b === NODE_END) {
      const top = stack.pop();
      flush(top, pos);
      close(top);
      pos += 1;
      segStart = pos;
    } else {
      pos += 1;
    }
  }
  return root;
}

// ---------------------------------------------------------------- items OTB
/** server id -> {cid, group, flags} (Map). Mismo truco que mapdata: 20001..20099 -> 1..99. */
export function loadOtb(path = PATHS.otb) {
  const root = parseTree(readFileSync(path));
  const out = new Map();
  for (const node of root.children) {
    const p = node.props;
    const dv = new DataView(p.buffer, p.byteOffset, p.byteLength);
    const flags = p.length >= 4 ? dv.getUint32(0, true) : 0;
    let pos = 4, sid = null, cid = 0;
    while (pos + 3 <= p.length) {
      const attr = p[pos], size = dv.getUint16(pos + 1, true);
      if (attr === 0x10) sid = dv.getUint16(pos + 3, true);
      else if (attr === 0x11) cid = dv.getUint16(pos + 3, true);
      pos += 3 + size;
    }
    if (sid === null) continue;
    if (sid > 20000 && sid < 20100) sid -= 20000;
    out.set(sid, { cid, flags, group: OTB_GROUPS[node.type] ?? `g${node.type}` });
  }
  return out;
}

// ---------------------------------------------------------------- Tibia.dat
export function parseDat(path = PATHS.dat) {
  const d = readFileSync(path);
  const dv = new DataView(d.buffer, d.byteOffset, d.byteLength);
  const nItems = dv.getUint16(4, true);
  let pos = 12;
  const out = new Map();
  for (let cid = 100; cid <= nItems; cid++) {
    const e = { cid, rank: RANK_COMMON, dx: 0, dy: 0, elev: 0, minimap: -1, unpassable: false,
      floorChange: false, w: 1, h: 1, layers: 1, px: 1, py: 1, pz: 1, frames: 1, sprites: null };
    let rankSet = false;
    for (;;) {
      const f = d[pos++];
      if (f === 0xff) break;
      if (f >= 0x20) throw new Error(`flag de dat inválido ${f} en cid ${cid}`);
      const a = pos;
      pos += DAT_ARGS[f] ?? 0;
      if (!rankSet && f <= 0x03) { e.rank = [RANK_GROUND, RANK_BORDER, RANK_BOTTOM, RANK_TOP][f]; rankSet = true; }
      if (f === 0x0c) e.unpassable = true;
      else if (f === 0x17) e.floorChange = true;
      else if (f === 0x18) { e.dx = dv.getUint16(a, true); e.dy = dv.getUint16(a + 2, true); }
      else if (f === 0x19) e.elev = dv.getUint16(a, true);
      else if (f === 0x1c) e.minimap = dv.getUint16(a, true);
    }
    e.w = d[pos]; e.h = d[pos + 1];
    pos += 2;
    if (e.w > 1 || e.h > 1) pos += 1;
    [e.layers, e.px, e.py, e.pz, e.frames] = d.subarray(pos, pos + 5);
    pos += 5;
    const n = e.w * e.h * e.layers * e.px * e.py * e.pz * e.frames;
    e.sprites = new Uint16Array(n);
    for (let i = 0; i < n; i++) e.sprites[i] = dv.getUint16(pos + 2 * i, true);
    pos += 2 * n;
    out.set(cid, e);
  }
  return out;
}

/** Color de minimapa 7.6 (cubo 6x6x6) a RGB. */
export function minimapRgb(c) {
  return [Math.floor(c / 36) % 6 * 51, Math.floor(c / 6) % 6 * 51, c % 6 * 51];
}

// ---------------------------------------------------------------- Tibia.spr
/** Decodifica cada sprite una sola vez y guarda versiones reducidas por escala (32,16,8,4,2,1). */
export class Sprites {
  constructor(path = PATHS.spr) {
    this.d = readFileSync(path);
    this.dv = new DataView(this.d.buffer, this.d.byteOffset, this.d.byteLength);
    this.count = this.dv.getUint16(4, true);
    this.byScale = new Map(); // s -> Map(sid -> Uint8Array s*s*4 | null)
    this.decoded = 0;
  }

  /** RGBA 32x32 (alfa 0/255) o null si está vacío. */
  decode(sid) {
    if (sid <= 0 || sid > this.count) return null;
    const off = this.dv.getUint32(6 + (sid - 1) * 4, true);
    if (!off) return null;
    const size = this.dv.getUint16(off + 3, true);
    const d = this.d;
    const px = new Uint8Array(32 * 32 * 4);
    let p = off + 5, i = 0, any = false;
    const end = p + size;
    while (p < end && i < 1024) {
      const t = this.dv.getUint16(p, true), c = this.dv.getUint16(p + 2, true);
      p += 4; i += t;
      for (let k = 0; k < c; k++, i++, p += 3) {
        if (i < 1024) {
          const o = i * 4;
          px[o] = d[p]; px[o + 1] = d[p + 1]; px[o + 2] = d[p + 2]; px[o + 3] = 255;
          any = true;
        }
      }
    }
    this.decoded++;
    return any ? px : null;
  }

  /** Sprite reducido a s x s (promedio con alfa; s divide a 32). */
  get(sid, s) {
    let m = this.byScale.get(s);
    if (!m) this.byScale.set(s, (m = new Map()));
    let v = m.get(sid);
    if (v !== undefined) return v;
    if (s === 32) v = this.decode(sid);
    else {
      const src = this.get(sid, 32);
      v = src ? downscale(src, 32, s) : null;
    }
    m.set(sid, v);
    return v;
  }
}

function downscale(src, n, s) {
  const f = n / s, out = new Uint8Array(s * s * 4), area = f * f;
  for (let y = 0; y < s; y++) for (let x = 0; x < s; x++) {
    let r = 0, g = 0, b = 0, a = 0;
    for (let yy = 0; yy < f; yy++) {
      let o = ((y * f + yy) * n + x * f) * 4;
      for (let xx = 0; xx < f; xx++, o += 4) {
        const al = src[o + 3];
        if (al) { r += src[o] * al; g += src[o + 1] * al; b += src[o + 2] * al; a += al; }
      }
    }
    const o = (y * s + x) * 4;
    if (a) { out[o] = r / a; out[o + 1] = g / a; out[o + 2] = b / a; out[o + 3] = Math.round(a / area); }
  }
  return out;
}

// ---------------------------------------------------------------- OTBM
/** Mapa: floors[z] = Map(y -> fila ordenada por x de {x, y, z, items: number[], flags, house}). */
export class GameMap {
  constructor(buf, label = 'map') {
    this.label = label;
    this.hash = createHash('sha1').update(buf).digest('hex').slice(0, 12);
    this.tiles = new Map(); // key -> tile
    this.bbox = { x0: 1e9, y0: 1e9, x1: -1, y1: -1 };
    const root = parseTree(buf);
    const mapNode = root.children[0];
    for (const area of mapNode.children) {
      if (area.type !== T_AREA) continue;
      const ap = area.props;
      const ax = ap[0] | (ap[1] << 8), ay = ap[2] | (ap[3] << 8), az = ap[4];
      for (const tile of area.children) {
        if (tile.type !== T_TILE && tile.type !== T_HOUSETILE) continue;
        const p = tile.props;
        const x = ax + p[0], y = ay + p[1];
        let pos = 2, house = 0, flags = 0;
        if (tile.type === T_HOUSETILE) { house = p[2] | (p[3] << 8) | (p[4] << 16) | (p[5] << 24); pos = 6; }
        const items = [];
        while (pos < p.length) {
          const attr = p[pos++];
          if (attr === 3) { flags = p[pos] | (p[pos + 1] << 8) | (p[pos + 2] << 16) | (p[pos + 3] << 24); pos += 4; }
          else if (attr === 9) { items.push(p[pos] | (p[pos + 1] << 8)); pos += 2; }
          else break;
        }
        for (const c of tile.children) {
          if (c.type === T_ITEM && c.props.length >= 2) items.push(c.props[0] | (c.props[1] << 8));
        }
        // firma de todo el contenido (atributos de ítems: action id, destino de teleport, texto, contenido
        // de cofres...) para que el diff también vea cambios que no cambian el sprite
        const t = { x, y, z: az, items, flags, house, sig: fnv(tile, 0x811c9dc5) };
        this.tiles.set(key(x, y, az), t);
        const b = this.bbox;
        if (x < b.x0) b.x0 = x; if (y < b.y0) b.y0 = y; if (x > b.x1) b.x1 = x; if (y > b.y1) b.y1 = y;
      }
    }
    // índice por piso y fila
    this.floors = new Map();
    for (const t of this.tiles.values()) {
      let f = this.floors.get(t.z);
      if (!f) this.floors.set(t.z, (f = { rows: new Map(), bbox: { x0: 1e9, y0: 1e9, x1: -1, y1: -1 }, count: 0 }));
      let r = f.rows.get(t.y);
      if (!r) f.rows.set(t.y, (r = []));
      r.push(t);
      f.count++;
      const b = f.bbox;
      if (t.x < b.x0) b.x0 = t.x; if (t.y < b.y0) b.y0 = t.y; if (t.x > b.x1) b.x1 = t.x; if (t.y > b.y1) b.y1 = t.y;
    }
    for (const f of this.floors.values()) for (const r of f.rows.values()) r.sort((a, b) => a.x - b.x);
  }

  get(x, y, z) { return this.tiles.get(key(x, y, z)); }

  /**
   * Copia del mapa con casillas reemplazadas (sin escribir nada): para ver una propuesta antes de
   * escribirla (p. ej. las celdas de mapkit). cells: [[x, y, z, [ids]], ...] o {"x,y,z": [ids]}.
   * Una lista vacía borra la casilla.
   */
  withCells(cells, label = 'cells') {
    const list = Array.isArray(cells) ? cells : Object.entries(cells).map(([k, v]) => [...k.split(',').map(Number), v]);
    const m = Object.create(GameMap.prototype);
    m.label = label;
    m.hash = createHash('sha1').update(this.hash + JSON.stringify(list)).digest('hex').slice(0, 12);
    m.bbox = { ...this.bbox };
    m.tiles = new Map(this.tiles);
    m.floors = new Map(this.floors);
    const touched = new Set();
    for (const [x, y, z, items] of list) {
      const old = m.tiles.get(key(x, y, z));
      const t = { x, y, z, items: items.map(Number), flags: old ? old.flags : 0, house: old ? old.house : 0, sig: 0 };
      t.sig = old && old.items.length === t.items.length && old.items.every((v, i) => v === t.items[i]) ? old.sig
        : fnv({ props: Uint8Array.from(t.items.flatMap((v) => [v & 255, v >> 8])), children: [] }, 7);
      if (items.length) m.tiles.set(key(x, y, z), t); else m.tiles.delete(key(x, y, z));
      let f = m.floors.get(z);
      if (!touched.has(`f${z}`)) {
        f = f ? { ...f, rows: new Map(f.rows), bbox: { ...f.bbox } } : { rows: new Map(), bbox: { x0: x, y0: y, x1: x, y1: y }, count: 0 };
        m.floors.set(z, f); touched.add(`f${z}`);
      }
      if (!touched.has(`r${z},${y}`)) { f.rows.set(y, [...(f.rows.get(y) || [])]); touched.add(`r${z},${y}`); }
      const row = f.rows.get(y), i = row.findIndex((r) => r.x === x);
      if (i >= 0) { if (items.length) row[i] = t; else row.splice(i, 1); }
      else if (items.length) { row.push(t); row.sort((a, b) => a.x - b.x); }
      const b = f.bbox;
      if (x < b.x0) b.x0 = x; if (y < b.y0) b.y0 = y; if (x > b.x1) b.x1 = x; if (y > b.y1) b.y1 = y;
    }
    return m;
  }

  /** Casillas del piso z dentro del rectángulo, en orden de dibujo (filas, luego x). */
  *region(x0, y0, x1, y1, z) {
    const f = this.floors.get(z);
    if (!f) return;
    for (let y = y0; y <= y1; y++) {
      const r = f.rows.get(y);
      if (!r) continue;
      let lo = 0, hi = r.length;
      while (lo < hi) { const m = (lo + hi) >> 1; if (r[m].x < x0) lo = m + 1; else hi = m; }
      for (let i = lo; i < r.length && r[i].x <= x1; i++) yield r[i];
    }
  }
}

function fnv(node, h) {
  const p = node.props;
  for (let i = 0; i < p.length; i++) h = Math.imul(h ^ p[i], 16777619);
  h = Math.imul(h ^ 0xfe, 16777619);
  for (const c of node.children) h = fnv(c, h);
  return Math.imul(h ^ 0xff, 16777619);
}

export const key = (x, y, z) => (z * 65536 + y) * 65536 + x;

/** Lee un OTBM de un archivo o de git: "git:HEAD~1" o "git:HEAD~1:otra/ruta.otbm". */
export function readMapBytes(spec = PATHS.map) {
  if (['actual', 'current', 'test.otbm'].includes(spec)) spec = PATHS.map;
  if (spec.startsWith('git:')) {
    const rest = spec.slice(4);
    const i = rest.indexOf(':');
    const ref = i < 0 ? rest : rest.slice(0, i);
    const path = i < 0 ? relative(REPO, PATHS.map) : rest.slice(i + 1);
    return execFileSync('git', ['-C', REPO, 'show', `${ref}:${path}`], { maxBuffer: 1 << 30 });
  }
  return readFileSync(resolve(spec));
}

const mapCache = new Map();
export function loadMap(spec = PATHS.map) {
  if (['actual', 'current', 'test.otbm'].includes(spec)) spec = PATHS.map;
  const k = spec.startsWith('git:') ? spec : `${resolve(spec)}@${statSync(resolve(spec)).mtimeMs}`;
  let m = mapCache.get(k);
  if (!m) { m = new GameMap(readMapBytes(spec), spec); mapCache.set(k, m); }
  return m;
}

// ---------------------------------------------------------------- spawns
/** Monstruos y NPCs de test-spawn.xml como [{x, y, z, name}] (centro + desplazamiento). */
export function loadSpawns(path = PATHS.spawn) {
  const xml = readFileSync(path, 'utf8');
  const out = [];
  const attr = (s, k) => { const m = s.match(new RegExp(`\\b${k}="([^"]*)"`)); return m ? m[1] : null; };
  const re = /<spawn\b([^>]*)>([\s\S]*?)<\/spawn>/g;
  let m;
  while ((m = re.exec(xml))) {
    const cx = +attr(m[1], 'centerx'), cy = +attr(m[1], 'centery'), cz = +attr(m[1], 'centerz');
    const inner = /<(monster|npc)\b([^>]*)\/?>/g;
    let n;
    while ((n = inner.exec(m[2]))) {
      const z = attr(n[2], 'z');
      out.push({ kind: n[1], name: attr(n[2], 'name'), x: cx + +(attr(n[2], 'x') ?? 0),
        y: cy + +(attr(n[2], 'y') ?? 0), z: z === null ? cz : +z });
    }
  }
  return out;
}

// ---------------------------------------------------------------- todo junto
export class Assets {
  constructor() {
    const t0 = performance.now();
    this.otb = loadOtb();
    this.dat = parseDat();
    this.spr = new Sprites();
    // server id -> entrada del dat (con flags de OTB)
    this.entries = new Map();
    for (const [sid, o] of this.otb) {
      const e = o.cid ? this.dat.get(o.cid) : null;
      if (e) this.entries.set(sid, { ...e, sid, otbFlags: o.flags, group: o.group });
    }
    this.loadMs = performance.now() - t0;
    const fp = [PATHS.otb, PATHS.dat, PATHS.spr].map((p) => { const s = statSync(p); return `${s.size}:${s.mtimeMs}`; });
    this.fingerprint = createHash('sha1').update(fp.join('|')).digest('hex').slice(0, 10);
  }
}
