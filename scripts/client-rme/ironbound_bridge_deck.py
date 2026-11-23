"""Basalt pavement, brass choke markings and piers, exclusive to the main bridge."""
from functools import lru_cache
from PIL import Image, ImageDraw
from city_bridge_z6_art import DECK, NARROW, TRAPDOORS, OUT_DIR, D

FLOOR_BASE, FLOOR_CLIENT = 20540, 5260
PIER_ID, PIER_CLIENT = 20579, 5299
PIER_POSITIONS = {(139, 65), (141, 65), (139, 69), (141, 69),
                  (139, 72), (142, 72), (139, 75), (142, 75)}
SIDES = {'n': (0, -1), 'e': (1, 0), 's': (0, 1), 'w': (-1, 0)}


def key_for(x, y):
    edges = ''.join(s for s, (dx, dy) in SIDES.items() if (x + dx, y + dy) not in DECK)
    narrow = any(a <= y <= b for a, b in NARROW)
    band = 'n' if y in (66, 72) else 's' if y in (61, 67) else ''
    return edges, narrow, band


def pavement(key):
    edges, narrow, band = key
    image = Image.new('RGBA', (32, 32), '#121c29')
    draw = ImageDraw.Draw(image)
    for y in (0, 16):
        for x in (0, 16):
            c = (59, 73, 88) if (x + y) % 32 else (67, 80, 94)
            draw.rectangle((x + 1, y + 1, x + 15, y + 15), fill=c)
            draw.line((x + 1, y + 1, x + 15, y + 1), fill=(95, 109, 120))
            draw.line((x + 1, y + 15, x + 15, y + 15), fill=(33, 44, 58))
    boxes = {'n': (0, 0, 31, 2), 's': (0, 29, 31, 31),
             'w': (0, 0, 2, 31), 'e': (29, 0, 31, 31)}
    for side in edges:
        draw.rectangle(boxes[side], fill=(165, 182, 189))
    if narrow:
        for x in (3, 26):
            draw.rectangle((x, 0, x + 2, 31), fill=(171, 113, 47))
            for y in (5, 21):
                draw.rectangle((x, y, x + 1, y + 1), fill=(243, 196, 105))
        for y in (9, 25):
            draw.line((12, y, 19, y), fill=(190, 143, 71))
    # Fine deterministic mineral flecks; leave mortar and metal edges untouched.
    for y in range(3, 29):
        for x in range(5, 27):
            if (x * 31 + y * 47 + x * y) % 19 == 0:
                r, g, b, a = image.getpixel((x, y))
                if b > r:
                    image.putpixel((x, y), (r + 9, g + 9, b + 9, a))
    if band:
        y = 2 if band == 'n' else 26
        draw.rectangle((0, y, 31, y + 3), fill=(169, 111, 47))
        draw.line((0, y, 31, y), fill=(242, 198, 115))
        for x in (5, 15, 25):
            draw.point((x, y + 2), fill=(255, 223, 154))
    return image


@lru_cache(maxsize=1)
def floor_pieces():
    keys = sorted({key_for(x, y) for x, y in DECK - TRAPDOORS})
    assert len(keys) < PIER_ID - FLOOR_BASE
    return [(key, pavement(key)) for key in keys]


def floor_placements():
    ids = {key: FLOOR_BASE + i for i, (key, _) in enumerate(floor_pieces())}
    return {(x, y): ids[key_for(x, y)] for x, y in DECK - TRAPDOORS}


def items():
    out = [dict(name='ironbound bridge pavement', server_id=FLOOR_BASE + i,
                client_id=FLOOR_CLIENT + i, prototype=1794, decor=True, fixed=True,
                png=f'ironbound_floor_{i:02d}.png',
                descr='Basalt paving and bronze inlays on the city bridge.')
           for i, _ in enumerate(floor_pieces())]
    out.append(dict(name='ironbound bridge pier', server_id=PIER_ID, client_id=PIER_CLIENT,
                    prototype=1277, decor=True, fixed=True, tiles=2, png='ironbound_pier.png',
                    descr='A basalt pier braced with bronze collars.'))
    return out


def prepare():
    for i, (_, image) in enumerate(floor_pieces()):
        image.save(OUT_DIR / f'ironbound_floor_{i:02d}.png')
    boxes = [D.Box(23, 31, 23, 31, 0, 22, *D.STONE),
             D.Box(22, 32, 22, 32, 5, 8, *D.BRONZE),
             D.Box(22, 32, 22, 32, 15, 17, *D.BRONZE),
             D.Box(21, 33, 21, 33, 21, 24, *D.STONE)]
    image = D.render_piece(boxes, (0, 40, 0, 40), (-32, -32), (64, 64))
    source = image.copy()
    for y in range(64):
        for x in range(64):
            r, g, b, a = source.getpixel((x, y))
            if not a:
                continue
            if any(not (0 <= x + dx < 64 and 0 <= y + dy < 64)
                   or not source.getpixel((x + dx, y + dy))[3]
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                image.putpixel((x, y), D.OUTLINE + (255,))
            else:
                k = D.grain(x, y)
                image.putpixel((x, y), (int(r * k), int(g * k), int(b * k), 255))
    image.save(OUT_DIR / 'ironbound_pier.png')
