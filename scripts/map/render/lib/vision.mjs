// "Evaluar con modelo": una imagen chica + una pregunta corta -> JSON validado (OpenRouter, solo mapas).
// Mismas convenciones que scripts/map/mapkit/jev.py: clave en OPENROUTER_API_KEY o
// ~/.config/retro76/openrouter.env (nunca se imprime), log en ~/.cache/retro76/jev-log.jsonl,
// tope de gasto, validación del JSON con un reintento y fallback (sin clave => no llama).
import { createHash } from 'node:crypto';
import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';

// Medido el 26 nov 2026 con preguntas de respuesta conocida (docs/map-rendering.md#modelos):
// qwen3.7-flash falló todo; jev-router con razonamiento gasta los tokens pensando y no contesta.
export const MODELS = {
  normal: 'deepseek/deepseek-v4.1-flash-1017', // 4/4 correctas, ~US$0,00003–0,00008 por imagen
  barato: 'inclusionai/ling-3.0-flash-vl', // 5/6, ~US$0,00001–0,00004
  gemma: 'google/gemma-3-27b-it', // 5/6, ~US$0,00003
  segunda: 'anthropic/claude-haiku-5.5', // 2/2, ~US$0,0001: segunda opinión
  jev: 'typesafe/jev-router', // elige solo; 3/4, ~US$0,00006–0,00013 y más lento
};
export const DEFAULT_MODEL = process.env.MAPRENDER_VISION_MODEL || MODELS.normal;
const URL = 'https://openrouter.ai/api/v1/chat/completions';
const LOG = `${homedir()}/.cache/retro76/jev-log.jsonl`;
const SPENT = `${homedir()}/.cache/retro76/maprender-spent.json`;
const CACHE = `${homedir()}/.cache/retro76/maprender-ask`;
const ENV_FILE = `${homedir()}/.config/retro76/openrouter.env`;
const SYSTEM = 'You review top-down renders of a Tibia 7.6 map (old 2D tile MMORPG, 1 tile = 1 square). '
  + 'Answer ONLY with one JSON object matching the requested shape. Be concrete and brief. '
  + 'When the image has coordinate rulers, refer to places by those tile coordinates.';

function apiKey() {
  if (process.env.OPENROUTER_API_KEY) return process.env.OPENROUTER_API_KEY;
  if (existsSync(ENV_FILE)) {
    for (let line of readFileSync(ENV_FILE, 'utf8').split('\n')) {
      line = line.trim().replace(/^export\s+/, '');
      if (line.startsWith('OPENROUTER_API_KEY=')) return line.slice(19).trim().replace(/^['"]|['"]$/g, '');
    }
  }
  return null;
}

/** Forma esperada: {"campo": "boolean"|"number"|"string"|"array"|"object"|"a|b|c" (enum)}. */
export function validate(ans, expect) {
  if (!ans || typeof ans !== 'object' || Array.isArray(ans)) throw new Error('no es un objeto');
  if (!expect) return ans;
  for (const [k, t] of Object.entries(expect)) {
    if (!(k in ans)) throw new Error(`falta "${k}"`);
    const v = ans[k];
    if (t === 'array' ? !Array.isArray(v) : t === 'object' ? (typeof v !== 'object' || Array.isArray(v) || v === null)
      : ['boolean', 'number', 'string'].includes(t) ? typeof v !== t : !t.split('|').includes(String(v))) {
      throw new Error(`"${k}" debería ser ${t}`);
    }
  }
  return ans;
}

/** Gasto acumulado del día (tope diario además del tope por llamada). */
function spentToday() {
  const day = new Date().toISOString().slice(0, 10);
  try { const s = JSON.parse(readFileSync(SPENT, 'utf8')); return s.day === day ? s.usd : 0; } catch { return 0; }
}
function addSpent(usd) {
  const day = new Date().toISOString().slice(0, 10);
  mkdirSync(`${homedir()}/.cache/retro76`, { recursive: true });
  writeFileSync(SPENT, JSON.stringify({ day, usd: spentToday() + usd }));
}

/**
 * Pregunta con imagen. images: [{buf, mime}]. Devuelve {ok, answer?, error?, meta}.
 * opts: model, expect, maxTokens, detail ('low'|'high'|'auto'), reasoning ('none'|'low'|...), noCache
 */
export async function ask(images, question, opts = {}) {
  const model = MODELS[opts.model] || opts.model || DEFAULT_MODEL;
  const expect = opts.expect || null;
  const maxDay = Number(process.env.MAPRENDER_VISION_MAX_USD || '0.20');
  const h = createHash('sha1').update(model + '\0' + question + '\0' + JSON.stringify(expect) + '\0' + (opts.detail || ''));
  for (const im of images) h.update(im.buf);
  const ck = `${CACHE}/${h.digest('hex')}.json`;
  if (!opts.noCache && existsSync(ck)) {
    const c = JSON.parse(readFileSync(ck, 'utf8'));
    return { ok: true, answer: c.answer, meta: { ...c.meta, cached: true, cost: 0 } };
  }
  const key = apiKey();
  if (!key) return { ok: false, error: 'sin OPENROUTER_API_KEY (fallback: no se evaluó)', meta: { skipped: true } };
  const already = spentToday();
  if (already >= maxDay) return { ok: false, error: `tope diario MAPRENDER_VISION_MAX_USD=${maxDay} alcanzado (US$${already.toFixed(4)})`, meta: { skipped: true } };

  const shape = expect ? `\nReturn JSON with exactly these keys: ${JSON.stringify(expect)} ("a|b" = one of those values).` : '\nReturn a JSON object.';
  const content = [{ type: 'text', text: question + shape }];
  for (const im of images) {
    const image_url = { url: `data:${im.mime};base64,${im.buf.toString('base64')}` };
    if (opts.detail) image_url.detail = opts.detail;
    content.push({ type: 'image_url', image_url });
  }
  const messages = [{ role: 'system', content: SYSTEM }, { role: 'user', content }];
  let last = { error: 'sin respuesta' }, total = 0;
  for (let attempt = 0; attempt < 2; attempt++) {
    const body = { model, messages, response_format: { type: 'json_object' }, usage: { include: true },
      max_tokens: opts.maxTokens || 400, temperature: 0 };
    if (opts.reasoning === 'none') body.reasoning = { enabled: false };
    else if (opts.reasoning) body.reasoning = { effort: opts.reasoning, exclude: true };
    const t0 = Date.now();
    let r, meta;
    try {
      const res = await fetch(URL, { method: 'POST', signal: AbortSignal.timeout(120000), headers: {
        Authorization: `Bearer ${key}`, 'Content-Type': 'application/json', 'X-Title': 'map renderer' },
      body: JSON.stringify(body) });
      r = await res.json();
      if (!res.ok || r.error) throw new Error(`HTTP ${res.status}: ${JSON.stringify(r.error || r).slice(0, 200)}`);
    } catch (e) {
      last = { error: String(e.message || e).slice(0, 300) };
      log({ key: 'ask', model, error: last.error });
      continue;
    }
    const u = r.usage || {};
    meta = { model: r.model, cost: u.cost || 0, prompt_tokens: u.prompt_tokens, completion_tokens: u.completion_tokens,
      reasoning_tokens: u.completion_tokens_details?.reasoning_tokens || 0, seconds: (Date.now() - t0) / 1000,
      image_bytes: images.reduce((a, im) => a + im.buf.length, 0) };
    addSpent(meta.cost);
    total += meta.cost;
    meta.cost_total = total; // con los reintentos
    log({ key: 'maprender-ask', ...meta, q: question.slice(0, 80) });
    let text = r.choices?.[0]?.message?.content || '';
    try {
      text = text.slice(text.indexOf('{'), text.lastIndexOf('}') + 1);
      const answer = validate(JSON.parse(text), expect);
      mkdirSync(CACHE, { recursive: true });
      writeFileSync(ck, JSON.stringify({ answer, meta, question }, null, 1));
      return { ok: true, answer, meta: { ...meta, attempts: attempt + 1 } };
    } catch (e) {
      last = { error: `respuesta inválida: ${e.message}`, raw: text.slice(0, 300), meta };
      messages.push({ role: 'assistant', content: text || '(vacío)' },
        { role: 'user', content: `Invalid answer (${e.message}). Reply again with ONLY the JSON object in the exact shape.` });
    }
  }
  return { ok: false, ...last, meta: last.meta || {} };
}

function log(rec) {
  mkdirSync(`${homedir()}/.cache/retro76`, { recursive: true });
  const t = new Date().toISOString().replace('T', ' ').slice(0, 19);
  appendFileSync(LOG, JSON.stringify({ t, ...rec }) + '\n');
}
