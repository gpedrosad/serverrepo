#!/usr/bin/env node
// maprender: render de mapas Tibia 7.6 sin GUI (OTBM + DAT + SPR) con sharp. Doc: docs/map-rendering.md
import { readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { createInterface } from 'node:readline';
import { Assets, PATHS, loadMap, loadSpawns } from './lib/assets.mjs';
import {
  Canvas, DIFF_COLORS, WALK, asciiWalk, boxBlur, clusters, densityGrid, diffTiles, heat,
  renderMinimap, renderRegion, renderWalk, walkClass,
} from './lib/render.mjs';
import { encode, gridOf, loadImage, titled, withGrid } from './lib/image.mjs';
import { DEFAULT_MODEL, ask } from './lib/vision.mjs';

const HELP = `uso: node scripts/map/render/maprender.mjs <comando> [opciones]   (doc: docs/map-rendering.md)

Región (todas las órdenes que dibujan):
  --r x0,y0,x1,y1,z       rectángulo     |  --c x,y,z[,radio]  centro (radio 15)  |  --floor z  piso entero
  --map ruta|git:REF      mapa (por defecto test.otbm; git:HEAD~1 = versión anterior)
  --cells f.json|-        casillas propuestas encima del mapa, sin escribir nada: [[x,y,z,[ids]],...]
Salida:  --out f.png|.webp|.jpg|.avif  --quality 80  --width N  --max-side N  --grid 10  --mark x,y[;x,y]

Comandos:
  region   sprites reales           --px 32|16|8|4|2|1 (8)  --above N (pisos de arriba/techos, 0)
  minimap  colores de minimapa      --px 1
  layer    walk|density|items|mods  --px 4  --over none|minimap|render  --radius N  --base git:HEAD (mods)
  ascii    transitabilidad en texto (1 carácter por casilla; exacto, barato solo en regiones chicas)
  diff     resumen de cambios entre dos mapas (JSON, todos los pisos)  --base git:HEAD
  compare  variantes de la misma región  --variant nombre=ruta|git:REF|cells:f.json|imagen.png (repetir)
           --diff (resalta lo distinto de la primera; --diff prev: de la anterior)  --cols N
  ask      evalúa una imagen con un modelo barato  --image f | (opciones de region)  --q "pregunta"
           --expect '{"ok":"boolean","issues":"array"}'  --model normal|barato|gemma|segunda|jev|<id> (${DEFAULT_MODEL})
           --max-side 512  --format jpeg  --quality 70  --reasoning none
  tile     x,y,z  -> ítems y flags de la casilla (JSON)
  batch    lee trabajos JSON por línea de stdin ({"cmd":"region","r":"...","out":"..."}); carga los assets una vez
  bench    mide tiempos con los assets reales`;

// ---------------------------------------------------------------- argumentos
function parseArgs(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) { o._.push(a); continue; }
    const k = a.slice(2);
    const v = argv[i + 1] !== undefined && !argv[i + 1].startsWith('--') ? argv[++i] : true;
    if (k === 'variant') (o.variant ||= []).push(v);
    else o[k] = v;
  }
  return o;
}

let A = null;
const assets = () => (A ||= new Assets());

function regionOf(o, map) {
  const R = regionRaw(o, map);
  if (![R.x0, R.y0, R.x1, R.y1, R.z].every(Number.isInteger)) throw new Error('región inválida: --r x0,y0,x1,y1,z | --c x,y,z[,radio]');
  return R;
}

function regionRaw(o, map) {
  if (o.r) {
    const [x0, y0, x1, y1, z] = String(o.r).split(',').map(Number);
    return { x0: Math.min(x0, x1), y0: Math.min(y0, y1), x1: Math.max(x0, x1), y1: Math.max(y0, y1), z };
  }
  if (o.c) {
    const [x, y, z, rr = 15] = String(o.c).split(',').map(Number);
    return { x0: x - rr, y0: y - rr, x1: x + rr, y1: y + rr, z };
  }
  if (o.floor !== undefined) {
    const z = Number(o.floor), f = map.floors.get(z);
    if (!f) throw new Error(`el piso ${z} no tiene casillas`);
    return { ...f.bbox, z };
  }
  throw new Error('falta la región: --r x0,y0,x1,y1,z | --c x,y,z[,radio] | --floor z');
}

/** Mapa de --map con --cells encima (archivo JSON, '-' = stdin, o el objeto `cells` de un trabajo de batch). */
function mapOf(o, spec = o.map || PATHS.map, cellsArg = o.cells) {
  const map = loadMap(spec);
  if (!cellsArg) return map;
  const cells = typeof cellsArg === 'object' ? cellsArg : JSON.parse(readFileSync(cellsArg === '-' ? 0 : cellsArg, 'utf8'));
  return map.withCells(cells.cells || cells);
}

const num = (v, d) => (v === undefined || v === true ? d : Number(v));
const outPath = (o, name, fmt = 'png') => o.out || `${tmpdir()}/maprender/${name}.${o.format || fmt}`;
const encOpts = (o) => ({ out: o.out, format: o.format, quality: num(o.quality, 80), width: o.width && Number(o.width),
  maxSide: o['max-side'] && Number(o['max-side']), lossless: !!o.lossless });

function marks(cv, o, R, px) {
  if (!o.mark) return;
  for (const p of String(o.mark).split(';')) {
    const [x, y] = p.split(',').map(Number);
    cv.outline((x - R.x0) * px, (y - R.y0) * px, px, px, [255, 40, 40], Math.max(1, px >> 3));
  }
}

async function finish(cv, o, R, px, name, extra = {}) {
  marks(cv, o, R, px);
  if (o.grid) cv = await withGrid(cv, { x0: R.x0, y0: R.y0, px, n: num(o.grid, 10) });
  const enc = await encode(cv, { ...encOpts(o), out: outPath(o, name) });
  return { out: enc.out ?? outPath(o, name), w: enc.w, h: enc.h, bytes: enc.bytes, format: enc.format, ...extra };
}

const tag = (R) => `${R.x0}_${R.y0}_${R.x1}_${R.y1}_z${R.z}`;

// ---------------------------------------------------------------- comandos
const commands = {
  async region(o) {
    const map = mapOf(o), R = regionOf(o, map), px = num(o.px, 8);
    const t0 = performance.now();
    const cv = renderRegion(assets(), map, { ...R, px, above: num(o.above, 0) });
    const draw_ms = Math.round(performance.now() - t0);
    return finish(cv, o, R, px, `region-${tag(R)}-${px}`, { draw_ms });
  },

  async minimap(o) {
    const map = mapOf(o), R = regionOf(o, map), px = num(o.px, 1);
    return finish(renderMinimap(assets(), map, { ...R, px }), o, R, px, `minimap-${tag(R)}-${px}`);
  },

  async layer(o) {
    const kind = o._[1] || o.kind;
    const map = mapOf(o), R = regionOf(o, map), px = num(o.px, 4);
    const over = o.over || (kind === 'walk' ? 'none' : 'minimap');
    const base = () => (over === 'render' && [32, 16, 8, 4, 2, 1].includes(px) ? renderRegion(assets(), map, { ...R, px })
      : over === 'minimap' ? dim(renderMinimap(assets(), map, { ...R, px }), 0.55) : new Canvas((R.x1 - R.x0 + 1) * px, (R.y1 - R.y0 + 1) * px, [0, 0, 0]));
    if (kind === 'walk') {
      const counts = {};
      let cv;
      if (over === 'none') cv = renderWalk(assets(), map, { ...R, px }, counts);
      else {
        cv = base();
        for (const t of map.region(R.x0, R.y0, R.x1, R.y1, R.z)) {
          const c = walkClass(assets(), t);
          counts[c] = (counts[c] || 0) + 1;
          if (c !== 'void' && c !== 'walk') cv.fill((t.x - R.x0) * px, (t.y - R.y0) * px, px, px, WALK[c].color, 0.55);
        }
      }
      return finish(cv, o, R, px, `walk-${tag(R)}-${px}`, { counts });
    }
    if (kind === 'density' || kind === 'items') {
      const what = kind === 'items' ? 'items' : 'monsters';
      const radius = num(o.radius, what === 'monsters' ? 3 : 0);
      const raw = densityGrid(assets(), map, what === 'monsters' ? loadSpawns() : [], { ...R, what });
      const g = boxBlur(raw, radius);
      let max = num(o.max, 0);
      if (!max) for (const v of g.g) if (v > max) max = v;
      const cv = base();
      for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
        const v = g.g[y * g.W + x];
        if (v > 0) cv.fill(x * px, y * px, px, px, heat(v / (max || 1)), 0.35 + 0.6 * Math.min(1, v / (max || 1)));
      }
      let total = 0;
      for (const v of raw.g) total += v;
      return finish(cv, o, R, px, `${what}-${tag(R)}-${px}`, { what, total, radius, max_per_window: max, hotspots: hotspots(g, R, radius) });
    }
    if (kind === 'mods') {
      const before = loadMap(o.base || 'git:HEAD');
      const d = diffTiles(before, map, R);
      const cv = over === 'none' ? new Canvas((R.x1 - R.x0 + 1) * px, (R.y1 - R.y0 + 1) * px, [0, 0, 0]) : base();
      for (const c of d) cv.fill((c.x - R.x0) * px, (c.y - R.y0) * px, px, px, DIFF_COLORS[c.kind], over === 'render' ? 0.4 : 0.7);
      const counts = {};
      for (const c of d) counts[c.kind] = (counts[c.kind] || 0) + 1;
      return finish(cv, o, R, px, `mods-${tag(R)}-${px}`, { base: o.base || 'git:HEAD', counts, zones: clusters(d).slice(0, 12) });
    }
    throw new Error('layer: walk | density | items | mods');
  },

  async ascii(o) {
    const map = mapOf(o), R = regionOf(o, map);
    const text = asciiWalk(assets(), map, R);
    if (o.out) { (await import('node:fs')).writeFileSync(o.out, text + '\n'); return { out: o.out, chars: text.length }; }
    process.stdout.write(text + '\n');
    return null;
  },

  async diff(o) {
    const cur = mapOf(o), before = loadMap(o.base || 'git:HEAD');
    const floors = new Set([...cur.floors.keys(), ...before.floors.keys()]);
    const out = { base: o.base || 'git:HEAD', map: o.map || 'test.otbm', floors: {} };
    for (const z of [...floors].sort((a, b) => a - b)) {
      if (o.floor !== undefined && Number(o.floor) !== z) continue;
      const b = { x0: 0, y0: 0, x1: 65535, y1: 65535, z };
      const d = diffTiles(before, cur, b);
      if (!d.length) continue;
      const counts = {};
      for (const c of d) counts[c.kind] = (counts[c.kind] || 0) + 1;
      out.floors[z] = { ...counts, zones: clusters(d).slice(0, num(o.zones, 8)) };
    }
    return out;
  },

  async compare(o) {
    const variants = (o.variant || []).map((v) => { const i = v.indexOf('='); return i < 0 ? [v, v] : [v.slice(0, i), v.slice(i + 1)]; });
    if (variants.length < 2) throw new Error('compare necesita al menos dos --variant nombre=ruta|git:REF|imagen.png');
    const px = num(o.px, 8), isImg = (s) => /\.(png|jpe?g|webp|avif)$/i.test(s);
    let R = null, first = null, prev = null;
    const panels = [], info = [];
    for (const [label, spec] of variants) {
      let cv, note = {};
      if (isImg(spec)) cv = await loadImage(spec);
      else {
        // "cells:propuesta.json" = el mapa de --map con esas casillas encima
        const map = spec.startsWith('cells:') ? mapOf(o, o.map || PATHS.map, spec.slice(6)) : loadMap(spec);
        R ||= regionOf(o, map);
        cv = renderRegion(assets(), map, { ...R, px, above: num(o.above, 0) });
        if (first && o.diff) {
          const d = diffTiles(o.diff === 'prev' ? prev : first, map, R);
          for (const c of d) {
            // a px chico el borde taparía todo: se tiñe; a 8 px o más, borde de color
            if (px >= 8) cv.outline((c.x - R.x0) * px, (c.y - R.y0) * px, px, px, DIFF_COLORS[c.kind], Math.max(1, px >> 3));
            else cv.fill((c.x - R.x0) * px, (c.y - R.y0) * px, px, px, DIFF_COLORS[c.kind], 0.4);
          }
          note = { [o.diff === 'prev' ? 'changed_vs_prev' : 'changed_vs_first']: d.length };
        }
        first ||= map;
        prev = map;
        marks(cv, o, R, px);
        if (o.grid) cv = await withGrid(cv, { x0: R.x0, y0: R.y0, px, n: num(o.grid, 10) });
      }
      panels.push(await titled(cv, label));
      info.push({ label, spec, ...note });
    }
    const cv = gridOf(panels, num(o.cols, variants.length <= 3 ? variants.length : 0));
    const enc = await encode(cv, { ...encOpts(o), out: outPath(o, `compare-${R ? tag(R) : 'img'}`) });
    return { out: outPath(o, `compare-${R ? tag(R) : 'img'}`), w: enc.w, h: enc.h, bytes: enc.bytes, variants: info };
  },

  async ask(o) {
    if (!o.q) throw new Error('ask necesita --q "pregunta"');
    let cv;
    if (o.image) cv = await loadImage(o.image);
    else {
      const map = mapOf(o), R = regionOf(o, map), px = num(o.px, 8);
      cv = renderRegion(assets(), map, { ...R, px, above: num(o.above, 0) });
      marks(cv, o, R, px);
      if (o.grid) cv = await withGrid(cv, { x0: R.x0, y0: R.y0, px, n: num(o.grid, 10) });
    }
    const fmt = o.format || 'jpeg';
    const enc = await encode(cv, { format: fmt, quality: num(o.quality, 70), maxSide: num(o['max-side'], 512), out: o.out });
    const expect = o.expect ? JSON.parse(o.expect) : null;
    const res = await ask([{ buf: enc.buf, mime: `image/${fmt}` }], String(o.q), {
      model: o.model, expect, maxTokens: num(o['max-tokens'], 400), detail: o.detail, reasoning: o.reasoning || 'none', noCache: !!o['no-cache'] });
    return { ...res, image: { w: enc.w, h: enc.h, bytes: enc.bytes, format: fmt } };
  },

  async tile(o) {
    const [x, y, z] = String(o._[1] || o.at).split(',').map(Number);
    const map = loadMap(o.map || PATHS.map), t = map.get(x, y, z), a = assets();
    if (!t) return { x, y, z, empty: true };
    return { x, y, z, pz: !!(t.flags & 1), house: t.house || undefined, walk: walkClass(a, t),
      items: t.items.map((sid) => { const e = a.entries.get(sid); return e ? { id: sid, cid: e.cid, group: e.group, size: `${e.w}x${e.h}`,
        layer: ['ground', 'border', 'bottom', 'common', 'top'][e.rank], block: !!(e.otbFlags & 1) } : { id: sid, missing: true }; }) };
  },

  async batch() {
    const rl = createInterface({ input: process.stdin });
    for await (const line of rl) {
      if (!line.trim()) continue;
      const job = JSON.parse(line);
      const o = { _: [job.cmd, ...(job.args || [])], ...job };
      try { console.log(JSON.stringify({ ok: true, ...(await commands[job.cmd](o)) })); }
      catch (e) { console.log(JSON.stringify({ ok: false, cmd: job.cmd, error: e.message })); }
    }
    return null;
  },

  async bench() {
    const T = (f) => { const t = performance.now(); const r = f(); return [Math.round(performance.now() - t), r]; };
    const TA = async (f) => { const t = performance.now(); const r = await f(); return [Math.round(performance.now() - t), r]; };
    const rows = [];
    const [ta] = T(() => assets());
    rows.push(['assets (otb+dat+spr)', ta]);
    const [tm, map] = T(() => loadMap(PATHS.map));
    rows.push([`otbm (${map.tiles.size} casillas)`, tm]);
    const R = { x0: 150, y0: 30, x1: 249, y1: 129, z: 7 };
    for (const px of [32, 8, 4]) {
      const [tr, cv] = T(() => renderRegion(assets(), map, { ...R, px }));
      const [tp, png] = await TA(() => encode(cv, { format: 'png' }));
      const [tw, webp] = await TA(() => encode(cv, { format: 'webp', quality: 80 }));
      const [tj, jpg] = await TA(() => encode(cv, { format: 'jpeg', quality: 70 }));
      rows.push([`100x100 casillas a ${px}px (${cv.w}x${cv.h}) dibujo`, tr]);
      rows.push([`  png ${(png.bytes / 1024).toFixed(0)}KB | webp q80 ${(webp.bytes / 1024).toFixed(0)}KB | jpeg q70 ${(jpg.bytes / 1024).toFixed(0)}KB (ms png/webp/jpeg)`, `${tp}/${tw}/${tj}`]);
    }
    const F = { ...map.floors.get(7).bbox, z: 7 };
    const [tmm, mm] = T(() => renderMinimap(assets(), map, { ...F, px: 1 }));
    const [tmp, mmp] = await TA(() => encode(mm, { format: 'png' }));
    rows.push([`minimapa z7 entero (${mm.w}x${mm.h}, png ${(mmp.bytes / 1024).toFixed(0)}KB) dibujo/png`, `${tmm}/${tmp}`]);
    const [tf4] = T(() => renderRegion(assets(), map, { ...F, px: 4 }));
    rows.push([`piso z7 entero a 4px (${(F.x1 - F.x0 + 1) * 4}x${(F.y1 - F.y0 + 1) * 4}) dibujo`, tf4]);
    const [tw] = T(() => renderWalk(assets(), map, { ...F, px: 1 }));
    rows.push(['capa walk z7 entera a 1px', tw]);
    const s = assets().spr;
    rows.push([`sprites decodificados (de ${s.count})`, s.decoded]);
    return { bench: rows.map(([k, v]) => `${String(v).padStart(9)}  ${k}`) };
  },
};

function dim(cv, f) {
  const d = cv.data;
  for (let i = 0; i < d.length; i += 4) { d[i] *= f; d[i + 1] *= f; d[i + 2] *= f; }
  return cv;
}

/** Máximos locales del mapa de densidad (para responder "dónde" en texto). */
function hotspots(g, R, radius, n = 8) {
  const cand = [];
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) { const v = g.g[y * g.W + x]; if (v > 0) cand.push([v, x, y]); }
  cand.sort((a, b) => b[0] - a[0]);
  const out = [], sep = Math.max(4, radius * 2 + 1);
  for (const [v, x, y] of cand) {
    if (out.length >= n) break;
    if (out.some((h) => Math.abs(h.x - R.x0 - x) < sep && Math.abs(h.y - R.y0 - y) < sep)) continue;
    out.push({ x: R.x0 + x, y: R.y0 + y, n: Math.round(v * 10) / 10 });
  }
  return out;
}

// ---------------------------------------------------------------- main
const o = parseArgs(process.argv.slice(2));
const cmd = o._[0];
if (!cmd || cmd === 'help' || o.help || !commands[cmd]) {
  console.log(HELP);
  process.exit(cmd && !commands[cmd] ? 1 : 0);
}
const t0 = performance.now();
try {
  const res = await commands[cmd](o);
  if (res) console.log(JSON.stringify({ ...res, ms: Math.round(performance.now() - t0) }, null, cmd === 'bench' || cmd === 'diff' ? 1 : 0));
  if (res && res.ok === false) process.exitCode = 2;
} catch (e) {
  console.error(`maprender ${cmd}: ${e.message}`);
  process.exit(1);
}
