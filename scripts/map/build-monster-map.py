#!/usr/bin/env python3
"""Mapa interactivo de monstruos: todos los pisos de test.otbm con cada spawn, NPC y zona.

Uso (desde la raíz del repo):
  python3 scripts/map/build-monster-map.py SALIDA/            # vista "como en el juego" (necesita Pillow)
  python3 scripts/map/build-monster-map.py SALIDA/ --minimap  # solo colores de minimapa, sin Pillow
Escribe SALIDA/monstruos.html y SALIDA/monstruos/: z*.png (minimapa), data.json, t/ (mosaicos con los
sprites del juego por nivel de zoom) y look/ (cada monstruo y NPC con su sprite y colores). La página usa
site.css y menu.js si están en SALIDA (sitio local de Retro76); sin ellos funciona igual.

Fuentes: server/YurOTS/ots/data/world/{test.otbm,test-spawn.xml,npc.xml,generated-*.json},
data/monster/monsters.xml (+ cada XML) y el Tibia.dat de RME para los colores del minimapa.
Solo lee el repo. Ver docs/items-and-map/MAPA_DE_MONSTRUOS.md.
"""
from __future__ import annotations

import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kb"))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # game_render.py
from mapdata import MAP, REPO, iter_tiles, load_otb, parse_dat, parse_tree, png_bytes  # noqa: E402

DATA = REPO / "server/YurOTS/ots/data"
WORLD = DATA / "world"
SIZE = 512

# Zonas con nombre que no salen de un manifiesto generated-*.json
ZONES = [
    {"name": "Ciudad (Retro76)", "z": 7, "box": [120, 18, 200, 80]},
    {"name": "Plaza de portales del templo", "z": 7, "box": [155, 43, 169, 52]},
    {"name": "Sala de entrenamiento", "z": 7, "box": [133, 4, 160, 18]},
    {"name": "Paso del Norte: campo y portal", "z": 7, "box": [178, 2, 190, 22]},
]


def floor_images(out: Path) -> dict:
    otb = load_otb()
    dat = parse_dat()
    color = {}
    for sid, e in otb.items():
        d = dat.get(e.get("cid")) if e.get("cid") else None
        if d and 0x1C in d["flags"]:
            color[sid] = struct.unpack("<H", d["flags"][0x1C])[0]
    floors: dict[int, bytearray] = {}
    counts: dict[int, int] = {}
    for x, y, z, items in iter_tiles(parse_tree(MAP.read_bytes())):
        if not (0 <= x < SIZE and 0 <= y < SIZE):
            continue
        img = floors.setdefault(z, bytearray(SIZE * SIZE * 4))
        c = None
        for i in items:
            if i in color:
                c = color[i]
        rgb = (60, 60, 66) if c is None else ((c // 36) % 6 * 51, (c // 6) % 6 * 51, c % 6 * 51)
        o = (y * SIZE + x) * 4
        img[o:o + 4] = bytes((*rgb, 255))
        counts[z] = counts.get(z, 0) + 1
    for z, img in floors.items():
        (out / f"z{z}.png").write_bytes(png_bytes(SIZE, SIZE, bytes(img)))
    return counts


def monster_info() -> dict:
    info = {}
    reg = ET.parse(DATA / "monster/monsters.xml").getroot()
    for m in reg.iter("monster"):
        name, f = m.get("name"), m.get("file")
        path = DATA / "monster" / f
        if not path.exists():
            continue
        txt = path.read_text(encoding="latin-1")

        def g(pat, default=0):
            mm = re.search(pat, txt)
            return int(mm.group(1)) if mm else default
        info[name.lower()] = {"name": name, "hp": g(r'<health now="(\d+)"'), "exp": g(r'experience="(\d+)"'),
                              "look": g(r'<look type="(\d+)"'), "speed": g(r'speed="(\d+)"'),
                              "colors": [g(r'<look [^>]*head="(\d+)"'), g(r'<look [^>]*body="(\d+)"'),
                                         g(r'<look [^>]*legs="(\d+)"'), g(r'<look [^>]*feet="(\d+)"')]}
    return info


def spawns(info: dict) -> list:
    txt = (WORLD / "test-spawn.xml").read_text(encoding="latin-1")
    root = ET.fromstring(re.sub(r"<\?xml[^>]*\?>", "", txt))
    out = []
    for sp in root.iter("spawn"):
        cx, cy, cz = int(sp.get("centerx")), int(sp.get("centery")), int(sp.get("centerz"))
        mons = []
        for m in sp.iter("monster"):
            key = m.get("name", "").lower()
            mons.append({"n": info.get(key, {}).get("name", m.get("name")),
                         "x": cx + int(m.get("x", 0)), "y": cy + int(m.get("y", 0)),
                         "z": int(m.get("z", cz)), "t": int(m.get("spawntime", 0))})
        if mons:
            out.append({"x": cx, "y": cy, "z": cz, "r": int(sp.get("radius", 1)), "m": mons})
    return out


def npcs() -> list:
    txt = (WORLD / "npc.xml").read_text(encoding="latin-1")
    txt = re.sub(r"<!--.*?-->", "", txt, flags=re.S)
    return [{"n": n.get("name"), "x": int(n.get("x")), "y": int(n.get("y")), "z": int(n.get("z"))}
            for n in ET.fromstring(re.sub(r"<\?xml[^>]*\?>", "", txt)).iter("npc")]


def npc_looks() -> dict:
    """nombre -> look, de data/npc/*.xml."""
    out = {}
    for f in (DATA / "npc").glob("*.xml"):
        txt = f.read_text(encoding="latin-1")
        name = re.search(r'<npc[^>]*name="([^"]+)"', txt)
        look = re.search(r"<look ([^>]*)>", txt)
        if name and look:
            at = dict(re.findall(r'(\w+)="(\d+)"', look.group(1)))
            out[name.group(1)] = {k: int(at.get(k, 0)) for k in ("type", "head", "body", "legs", "feet")}
    return out


def zones() -> list:
    out = list(ZONES)
    for f in sorted(WORLD.glob("generated-*.json")):
        d = json.loads(f.read_text())
        name = d.get("name", f.stem).replace("generated-", "").replace("-", " ").capitalize()
        box = d.get("box")
        if isinstance(box, dict) and {"x1", "y1", "x2", "y2"} <= box.keys():
            zs = box.get("z", 7)
            for z in (zs if isinstance(zs, list) else [zs]):
                out.append({"name": name, "z": z, "box": [box["x1"], box["y1"], box["x2"], box["y2"]]})
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        sys.exit(__doc__)
    site = Path(args[0])
    out = site / "monstruos"
    out.mkdir(parents=True, exist_ok=True)
    counts = floor_images(out)
    info = monster_info()
    data = {"size": SIZE, "floors": sorted(counts), "tiles": counts, "spawns": spawns(info), "npcs": npcs(),
            "zones": zones(), "monsters": {v["name"]: v for v in info.values()}}
    if "--minimap" not in sys.argv:
        try:
            import game_render  # noqa: PLC0415 (necesita Pillow)
        except ImportError:
            print("Sin Pillow: solo minimapa (python3 -m pip install pillow para la vista del juego)")
        else:
            print("render del juego: mosaicos…")
            data["game"] = game_render.render_tiles(MAP, out)
            used = {m["n"] for s in data["spawns"] for m in s["m"]}
            looks = {}
            for n in used:
                v = data["monsters"].get(n)
                if v and v["look"]:
                    h, b, l, f = v["colors"]
                    looks[n] = {"type": v["look"], "head": h, "body": b, "legs": l, "feet": f}
            for n, img in game_render.render_creatures(looks, out).items():
                data["monsters"][n].update(img)
            nl = npc_looks()
            nimg = game_render.render_creatures({n["n"]: nl[n["n"]] for n in data["npcs"] if n["n"] in nl}, out)
            for n in data["npcs"]:
                if n["n"] in nimg:
                    n.update(nimg[n["n"]])
            print(f"  criaturas: {sum(1 for v in data['monsters'].values() if 'img' in v)} monstruos, "
                  f"{len(nimg)} NPC con sprite")
    (out / "data.json").write_text(json.dumps(data, separators=(",", ":")))
    (site / "monstruos.html").write_text(PAGE, encoding="utf-8")
    nm = sum(len(s["m"]) for s in data["spawns"])
    print(f"OK {site / 'monstruos.html'}: {len(counts)} pisos, {len(data['spawns'])} spawns, {nm} monstruos, "
          f"{len(data['npcs'])} NPC, {len(data['zones'])} zonas")
    return 0


PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mapa de monstruos</title><link rel="stylesheet" href="site.css">
<style>
:root{--bg:#18181c;--card:#222228;--line:#33333b;--fg:#e6e6ea;--mut:#9a9aa6;--acc:#6cc6ff}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif}
.mut{color:var(--mut)}
.wrap{display:grid;grid-template-columns:1fr 320px;gap:12px;padding:8px 14px 14px;height:calc(100vh - 64px);box-sizing:border-box}
@media (max-width:900px){.wrap{grid-template-columns:1fr;height:auto}#stage{height:70vh}}
.left{display:flex;flex-direction:column;min-height:0}
.bar{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:8px}
.bar button,.bar label{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:5px 10px;cursor:pointer;font:inherit}
.bar button.on{border-color:var(--acc);color:var(--acc)}
.bar label{display:flex;gap:6px;align-items:center}
.bar .sep{width:1px;height:22px;background:var(--line);margin:0 4px}
#stage{position:relative;flex:1;min-height:300px;background:#0b0b0e;border:1px solid var(--line);border-radius:10px;overflow:hidden;cursor:grab}
#stage.drag{cursor:grabbing}
canvas{position:absolute;inset:0;width:100%;height:100%}
#tip{position:absolute;pointer-events:none;background:rgba(15,15,19,.95);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:13px;max-width:280px;display:none;z-index:5}
#tip b{color:var(--acc)}
#pos{font:12px ui-monospace,Menlo,monospace;color:var(--acc);min-width:110px}
.side{background:var(--card);border:1px solid var(--line);border-radius:10px;display:flex;flex-direction:column;min-height:0}
.side h2{font-size:15px;margin:0;padding:10px 12px 6px}
.side input{margin:0 12px 8px;padding:7px 9px;border-radius:6px;border:1px solid var(--line);background:#16161b;color:var(--fg);font:inherit}
#list{overflow:auto;flex:1;padding:0 6px 8px}
.row{display:grid;grid-template-columns:14px 1fr auto;gap:8px;align-items:center;padding:5px 6px;border-radius:6px;cursor:pointer}
.row:hover{background:#2a2a31}.row.on{background:#1e3a52}
.row i{width:12px;height:12px;border-radius:50%;display:block;border:1px solid #0008}
.row small{color:var(--mut);display:block;font-size:12px}
.row .c{font:12px ui-monospace,Menlo,monospace;color:var(--mut);text-align:right}
.legend{display:flex;flex-wrap:wrap;gap:8px 12px;padding:8px 12px;border-top:1px solid var(--line);font-size:12px;color:var(--mut)}
.legend span{display:flex;gap:5px;align-items:center}.legend i{width:10px;height:10px;border-radius:50%;display:block}
#sel{padding:0 12px 8px;font-size:13px;color:var(--mut);min-height:20px}
#sel button{background:#1e3a52;border:1px solid #2f5a7a;color:#8fd3ff;border-radius:5px;padding:2px 8px;cursor:pointer;font:inherit;font-size:12px}
</style></head><body><script src="menu.js"></script>
<div class="wrap"><div class="left">
<div class="bar" id="floors"></div>
<div class="bar">
<button id="zin" title="Acercar">＋</button><button id="zout" title="Alejar">－</button><button id="fit">Ver todo</button>
<span class="sep"></span>
<label><input type="checkbox" id="tGame" checked> Vista del juego</label>
<label><input type="checkbox" id="tSp" checked> Spawns</label>
<label><input type="checkbox" id="tNpc" checked> NPC</label>
<label><input type="checkbox" id="tZon"> Zonas</label>
<span class="sep"></span><span id="pos">—</span></div>
<div id="stage"><canvas id="cv"></canvas><div id="tip"></div></div>
</div>
<aside class="side"><h2>Monstruos <span class="mut" id="tot"></span></h2>
<input id="q" placeholder="Buscar monstruo o NPC…" autocomplete="off">
<div id="sel"></div>
<div id="list"></div>
<div class="legend"><span><i style="background:#5bd16a"></i>&lt; 50 exp</span><span><i style="background:#e6d24a"></i>&lt; 300</span><span><i style="background:#f39a3d"></i>&lt; 1000</span><span><i style="background:#ef5350"></i>&lt; 3000</span><span><i style="background:#c06cff"></i>3000+</span><span><i style="background:#fff;border-radius:2px"></i>NPC</span></div>
</aside></div>
<script>
const $=s=>document.querySelector(s), cv=$('#cv'), ctx=cv.getContext('2d'), stage=$('#stage'), tip=$('#tip');
let D, imgs={}, floor=7, sel=null, q='', view={x:0,y:0,k:2}, show={sp:1,npc:1,zon:0,game:1};
const st=(k,v)=>{try{if(v===undefined)return localStorage.getItem(k);localStorage.setItem(k,v)}catch(e){}};
const tier=e=>e<50?'#5bd16a':e<300?'#e6d24a':e<1000?'#f39a3d':e<3000?'#ef5350':'#c06cff';
const exp=n=>(D.monsters[n]||{}).exp||0;
fetch('monstruos/data.json').then(r=>r.json()).then(d=>{D=d;
  D.floors.forEach(z=>{const im=new Image();im.src=`monstruos/z${z}.png`;im.onload=draw;imgs[z]=im});
  const h=new URLSearchParams(location.hash.slice(1));
  floor=+(h.get('z')??st('mm-floor')??7); sel=h.get('m')||null;
  buildFloors(); buildList(); resize();
  if(h.get('x')){view.k=+h.get('k')||4;center(+h.get('x'),+h.get('y'))} else fit();
  if(sel)selectMonster(sel,false);
});
function spawnsOn(z){return D.spawns.filter(s=>s.z==z)}
function buildFloors(){
  const per={};D.spawns.forEach(s=>per[s.z]=(per[s.z]||0)+s.m.length);
  $('#floors').innerHTML='<span class="mut">Piso</span>'+D.floors.map(z=>`<button data-f="${z}" title="${D.tiles[z]} casillas">z${z}${z==7?' · superficie':''}${per[z]?` <span class="mut">(${per[z]})</span>`:''}</button>`).join('');
  document.querySelectorAll('[data-f]').forEach(b=>b.onclick=()=>setFloor(+b.dataset.f));
  mark();
}
function mark(){document.querySelectorAll('[data-f]').forEach(b=>b.classList.toggle('on',+b.dataset.f==floor))}
function setFloor(z){floor=z;st('mm-floor',z);mark();buildList();draw();hash()}
function buildList(){
  const agg={};D.spawns.forEach(s=>s.m.forEach(m=>{const a=agg[m.n]||(agg[m.n]={n:m.n,all:0,here:0,boss:0});a.all++;if(s.z==floor)a.here++;if(m.t>=1800)a.boss=1}));
  let rows=Object.values(agg);
  const npcs=D.npcs.filter(n=>!q||n.n.toLowerCase().includes(q));
  if(q)rows=rows.filter(r=>r.n.toLowerCase().includes(q));
  rows.sort((a,b)=>(b.here-a.here)||(b.all-a.all)||a.n.localeCompare(b.n));
  $('#tot').textContent=`(${D.spawns.reduce((t,s)=>t+s.m.length,0)})`;
  $('#list').innerHTML=rows.map(r=>{const m=D.monsters[r.n]||{};return `<div class="row${sel==r.n?' on':''}" data-m="${r.n}"><i style="background:${tier(m.exp||0)}"></i><div>${r.n}${r.boss?' ★':''}<small>${m.hp?m.hp+' hp · '+m.exp+' exp':''}</small></div><div class="c">${r.here}<br><span title="en todos los pisos">${r.all} tot</span></div></div>`}).join('')
   +(q&&npcs.length?'<h2>NPC</h2>'+npcs.map(n=>`<div class="row" data-npc="${n.x},${n.y},${n.z}"><i style="background:#fff;border-radius:2px"></i><div>${n.n}<small>${n.x}, ${n.y}, z${n.z}</small></div><div class="c">→</div></div>`).join(''):'');
  document.querySelectorAll('[data-m]').forEach(e=>e.onclick=()=>selectMonster(e.dataset.m==sel?null:e.dataset.m,true));
  document.querySelectorAll('[data-npc]').forEach(e=>e.onclick=()=>{const [x,y,z]=e.dataset.npc.split(',').map(Number);if(z!=floor)setFloor(z);view.k=Math.max(view.k,6);center(x,y)});
}
let hop=0;
function selectMonster(n,jump){sel=n;hop=0;buildList();
  if(!n){$('#sel').innerHTML='';draw();hash();return}
  const all=D.spawns.filter(s=>s.m.some(m=>m.n==n)), fl=[...new Set(all.map(s=>s.z))].sort((a,b)=>a-b);
  $('#sel').innerHTML=`<b style="color:var(--fg)">${n}</b>: ${all.length} spawns en ${fl.map(z=>'z'+z).join(', ')} <button id="next">Ir al siguiente</button>`;
  $('#next').onclick=()=>{const s=all[hop++%all.length];if(s.z!=floor)setFloor(s.z);view.k=Math.max(view.k,5);center(s.x,s.y)};
  if(jump&&!all.some(s=>s.z==floor)&&fl.length)setFloor(fl[0]);
  draw();hash();
}
function resize(){const r=stage.getBoundingClientRect(),dpr=devicePixelRatio||1;cv.width=r.width*dpr;cv.height=r.height*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);draw()}
addEventListener('resize',resize);
function fit(){const r=stage.getBoundingClientRect();view.k=Math.max(0.5,Math.min(r.width,r.height)/D.size);view.x=(r.width-D.size*view.k)/2;view.y=(r.height-D.size*view.k)/2;draw()}
function center(x,y){const r=stage.getBoundingClientRect();view.x=r.width/2-(x+.5)*view.k;view.y=r.height/2-(y+.5)*view.k;draw();hash()}
function zoomAt(f,px,py){const k2=Math.min(64,Math.max(.5,view.k*f));view.x=px-(px-view.x)*k2/view.k;view.y=py-(py-view.y)*k2/view.k;view.k=k2;draw();hash()}
const tcache={},lcache={};let raf=0;
function schedule(){if(!raf)raf=requestAnimationFrame(()=>{raf=0;draw()})}
function tileImg(z,L,key){const k=z+'/'+L+'/'+key;let im=tcache[k];if(!im){im=tcache[k]=new Image();im.onload=schedule;im.src=`monstruos/t/${z}/${L}/${key}.webp`}return im}
function lookImg(src){let im=lcache[src];if(!im){im=lcache[src]=new Image();im.onload=schedule;im.src='monstruos/'+src}return im}
function drawSprite(src,w,h,tx,ty,alpha){const im=lookImg(src);if(!(im.complete&&im.naturalWidth))return false;const k=view.k,W=w*k,H=h*k;
  ctx.globalAlpha=alpha;ctx.drawImage(im,view.x+(tx+1)*k-W-k*.25,view.y+(ty+1)*k-H-k*.25,W,H);ctx.globalAlpha=1;return true}
function draw(){if(!D)return;const r=stage.getBoundingClientRect();ctx.clearRect(0,0,r.width,r.height);
  const im=imgs[floor];ctx.imageSmoothingEnabled=false;if(im&&im.complete)ctx.drawImage(im,view.x,view.y,D.size*view.k,D.size*view.k);
  const G=D.game;
  if(G&&show.game){const L=Math.max(0,Math.min(G.levels-1,Math.floor(Math.log2(32/view.k)))),span=G.chunk*2**L,sz=span*view.k;
    G.sets=G.sets||{};const sk=floor+'/'+L,set=G.sets[sk]||(G.sets[sk]=new Set(((G.index[floor]||{})[L])||[]));
    ctx.imageSmoothingEnabled=view.k<32/2**L;
    const i0=Math.floor(-view.x/sz),j0=Math.floor(-view.y/sz),i1=Math.floor((r.width-view.x)/sz),j1=Math.floor((r.height-view.y)/sz);
    for(let i=i0;i<=i1;i++)for(let j=j0;j<=j1;j++){const key=i+'_'+j;if(!set.has(key))continue;const t=tileImg(floor,L,key);
      if(t.complete&&t.naturalWidth)ctx.drawImage(t,view.x+i*sz,view.y+j*sz,sz+.6,sz+.6)}
    ctx.imageSmoothingEnabled=false}
  const P=(x,y)=>[view.x+(x+.5)*view.k,view.y+(y+.5)*view.k];
  if(show.zon){ctx.lineWidth=1.5;ctx.font='12px system-ui';D.zones.filter(z=>z.z==floor).forEach(z=>{const [a,b]=P(z.box[0]-.5,z.box[1]-.5),[c,d]=P(z.box[2]+.5,z.box[3]+.5);ctx.strokeStyle='#6cc6ffaa';ctx.strokeRect(a,b,c-a,d-b);ctx.fillStyle='#6cc6ff';ctx.fillText(z.name,a+3,b+13)})}
  const close=view.k>=10;
  if(show.sp){spawnsOn(floor).forEach(s=>{const has=sel?s.m.some(m=>m.n==sel):true;
    if(close){s.m.forEach(m=>{const mi=D.monsters[m.n]||{},a=sel&&m.n!=sel?.3:1;
        if(sel&&m.n==sel){const [x,y]=P(m.x,m.y);ctx.beginPath();ctx.ellipse(x,y+view.k*.3,view.k*.55,view.k*.25,0,0,7);ctx.strokeStyle='#ffd54a';ctx.lineWidth=2;ctx.stroke()}
        if(!(mi.img&&drawSprite(mi.img,mi.w,mi.h,m.x,m.y,a))){const [x,y]=P(m.x,m.y);ctx.globalAlpha=a;ctx.beginPath();ctx.arc(x,y,view.k*.3,0,7);ctx.fillStyle=tier(mi.exp||0);ctx.fill();ctx.globalAlpha=1}
        if(view.k>=22&&(!sel||m.n==sel)){const [x,y]=P(m.x,m.y);ctx.font='bold 11px system-ui';ctx.lineWidth=3;ctx.strokeStyle='#000c';ctx.strokeText(m.n,x-ctx.measureText(m.n).width/2,y-view.k*.95);ctx.fillStyle=tier(mi.exp||0);ctx.fillText(m.n,x-ctx.measureText(m.n).width/2,y-view.k*.95)}});return}
    const [x,y]=P(s.x,s.y);const top=s.m.reduce((a,m)=>exp(m.n)>exp(a.n)?m:a,s.m[0]);const rad=Math.max(3,Math.min(10,2+Math.sqrt(s.m.length)*2))*Math.min(1.6,Math.max(.7,view.k/3));
    ctx.globalAlpha=has?1:.15;ctx.beginPath();ctx.arc(x,y,rad,0,7);ctx.fillStyle=tier(exp(top.n));ctx.fill();ctx.lineWidth=has&&sel?2.5:1;ctx.strokeStyle=has&&sel?'#fff':'#000a';ctx.stroke();
    if(s.m.some(m=>m.t>=1800)){ctx.fillStyle='#fff';ctx.font='bold 11px system-ui';ctx.fillText('★',x+rad,y-rad)}ctx.globalAlpha=1})}
  if(show.npc){D.npcs.filter(n=>n.z==floor).forEach(n=>{const [x,y]=P(n.x,n.y);
    if(close&&n.img&&drawSprite(n.img,n.w,n.h,n.x,n.y,1)){}else{const s=Math.max(4,Math.min(9,view.k*.8));ctx.fillStyle='#fff';ctx.fillRect(x-s/2,y-s/2,s,s);ctx.strokeStyle='#000';ctx.strokeRect(x-s/2,y-s/2,s,s)}
    if(view.k>=14){ctx.font='bold 11px system-ui';ctx.lineWidth=3;ctx.strokeStyle='#000c';const w=ctx.measureText(n.n).width;ctx.strokeText(n.n,x-w/2,y-view.k*.95);ctx.fillStyle='#fff';ctx.fillText(n.n,x-w/2,y-view.k*.95)}})}
}
function hash(){const r=stage.getBoundingClientRect(),cx=Math.round((r.width/2-view.x)/view.k),cy=Math.round((r.height/2-view.y)/view.k);
  history.replaceState(null,'',`#z=${floor}&x=${cx}&y=${cy}&k=${view.k.toFixed(1)}${sel?'&m='+encodeURIComponent(sel):''}`)}
let drag=null;
stage.onmousedown=e=>{drag={x:e.clientX,y:e.clientY,vx:view.x,vy:view.y,moved:0};stage.classList.add('drag')};
addEventListener('mouseup',()=>{if(drag){stage.classList.remove('drag');if(drag.moved)hash()}drag=null});
stage.onmousemove=e=>{const r=stage.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
  if(drag){view.x=drag.vx+e.clientX-drag.x;view.y=drag.vy+e.clientY-drag.y;drag.moved=1;draw();tip.style.display='none';return}
  const tx=Math.floor((mx-view.x)/view.k),ty=Math.floor((my-view.y)/view.k);$('#pos').textContent=`${tx}, ${ty}, ${floor}`;
  let best=null,bd=1e9;if(show.sp)spawnsOn(floor).forEach(s=>{const d=Math.hypot(view.x+(s.x+.5)*view.k-mx,view.y+(s.y+.5)*view.k-my);if(d<bd){bd=d;best=s}});
  let npc=null;if(show.npc)D.npcs.filter(n=>n.z==floor).forEach(n=>{const d=Math.hypot(view.x+(n.x+.5)*view.k-mx,view.y+(n.y+.5)*view.k-my);if(d<Math.max(8,view.k)&&d<bd){bd=d;npc=n;best=null}});
  if(npc){tip.innerHTML=`<b>${npc.n}</b> (NPC)<br>${npc.x}, ${npc.y}, z${npc.z}`}
  else if(best&&bd<Math.max(12,view.k*1.5)){const g={};best.m.forEach(m=>g[m.n]=(g[m.n]||0)+1);
    tip.innerHTML=Object.entries(g).map(([n,c])=>{const m=D.monsters[n]||{};return `<b>${n}</b> ×${c}<br><span class="mut">${m.hp||'?'} hp · ${m.exp||0} exp · respawn ${best.m.find(x=>x.n==n).t}s</span>`}).join('<br>')+`<br><span class="mut">centro ${best.x}, ${best.y}, z${best.z} · radio ${best.r}</span>`}
  else {tip.style.display='none';return}
  tip.style.display='block';tip.style.left=Math.min(mx+14,r.width-290)+'px';tip.style.top=Math.min(my+14,r.height-120)+'px'};
stage.onmouseleave=()=>{tip.style.display='none';$('#pos').textContent='—'};
stage.onwheel=e=>{e.preventDefault();const r=stage.getBoundingClientRect();zoomAt(e.deltaY<0?1.25:0.8,e.clientX-r.left,e.clientY-r.top)};
stage.ondblclick=e=>{const r=stage.getBoundingClientRect();zoomAt(2,e.clientX-r.left,e.clientY-r.top)};
$('#zin').onclick=()=>{const r=stage.getBoundingClientRect();zoomAt(1.5,r.width/2,r.height/2)};
$('#zout').onclick=()=>{const r=stage.getBoundingClientRect();zoomAt(1/1.5,r.width/2,r.height/2)};
$('#fit').onclick=fit;
$('#tGame').onchange=e=>{show.game=e.target.checked;draw()};$('#tSp').onchange=e=>{show.sp=e.target.checked;draw()};$('#tNpc').onchange=e=>{show.npc=e.target.checked;draw()};$('#tZon').onchange=e=>{show.zon=e.target.checked;draw()};
$('#q').oninput=e=>{q=e.target.value.trim().toLowerCase();buildList()};
</script></body></html>
"""

if __name__ == "__main__":
    sys.exit(main())
