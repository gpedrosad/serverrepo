#!/usr/bin/env python3
"""Original 32 px grid artwork for the Seller district and Tonka's gem arcade."""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[2] / 'devtools/zagan-test/custom-sprites'
BASE, CLIENT = 20600, 6000
FLOORS = ('arcade', 'seller', 'house', 'gallery', 'terrace', 'roof', 'tonka', 'threshold')
WALLS = {
    1037: 'h', 1038: 'post', 1039: 'h', 1041: 'v', 1042: 'hv',
    1043: 'v', 1044: 'hv', 1045: 'h', 1046: 'hv', 1263: 'hw', 1264: 'vw',
}
FURNITURE = {1620: '1x2', 1621: '1x2', 1622: 1, 1623: 1,
             1624: 2, 1626: 2, 1627: 2, 1628: 2, 1629: 2}
ROOF_EDGES = {921: 'h', 922: 'v', 923: 'hv'}
RAILS = {1594: '1x2', 1596: '1x2', 1598: 1, 1600: '2x1'}
FLOOR_IDS = {key: BASE + i for i, key in enumerate(FLOORS)}
PROTOTYPES = tuple(WALLS) + tuple(FURNITURE) + tuple(ROOF_EDGES) + tuple(RAILS)
REPLACEMENTS = {sid: BASE + len(FLOORS) + i for i, sid in enumerate(PROTOTYPES)}
TONKA_COUNTER = BASE + len(FLOORS) + len(PROTOTYPES)
TONKA_DIVIDER = TONKA_COUNTER + 1
TONKA_CREST = TONKA_COUNTER + 2
SELLER_DISPLAY = TONKA_COUNTER + 3
TONKA_SIDE = SELLER_DISPLAY + 4

LIMESTONE = '#c2b49b'
PALE = '#ece0c2'
JOINT = '#a39785'
COPPER = '#b47852'
COPPER_LIGHT = '#e7af7b'
JADE = '#39796c'
JADE_LIGHT = '#75b8a0'
DARK = '#253c38'


def floor(key):
    palette = {
        'arcade': ('#948c7b', '#b7ab91', '#e1d3b7'),
        'seller': ('#9e9d87', '#d5ccb2', '#f0e3c6'),
        'house': ('#9b7759', '#bf9c73', '#e3c49a'),
        'gallery': ('#515a51', '#899386', '#b2b9a1'),
        'terrace': ('#758176', '#b6beaa', '#dbe0c7'),
        'roof': ('#22483e', JADE, '#6ba08a'),
        'tonka': ('#355e54', '#558b7a', '#8cbaa0'),
        'threshold': ('#6b756b', '#a0ada0', '#cfdbca'),
    }
    mortar, body, highlight = palette[key]
    im = Image.new('RGBA', (32, 32), mortar)
    d = ImageDraw.Draw(im)
    if key == 'roof':
        for y in range(0, 32, 8):
            for x in range(-8 if y % 16 else 0, 32, 16):
                d.rectangle((x+1, y, x+15, y+6), fill=body)
                d.line((x+1, y, x+15, y), fill=highlight)
                d.line((x+4, y+3, x+12, y+3), fill='#4e8a77')
        return im
    for y in (0, 16):
        for x in (0, 16):
            d.rectangle((x+1, y+1, x+15, y+15), fill=body)
            d.line((x+2, y+1, x+14, y+1), fill=highlight)
            for n in range(4):
                d.point((x+3+(n*7+y)%11, y+4+(n*3+x)%9), fill=highlight)
    if key == 'house':
        for y in (3, 19):
            d.line((2,y+7,9,y,14,y+5), fill='#aa855f')
            d.line((18,y+7,25,y,30,y+5), fill='#aa855f')
            for x in (14,30):
                d.point((x,y+10), fill='#f4dbc0')
    if key in ('seller', 'tonka', 'threshold', 'gallery'):
        for x, y in ((0, 0), (16, 16)):
            d.polygon(((x+8,y+4),(x+12,y+8),(x+8,y+12),(x+4,y+8)), fill=JADE if key != 'tonka' else DARK)
            d.line((x+7,y+6,x+9,y+6), fill=JADE_LIGHT)
    if key == 'threshold':
        d.line((0, 0, 31, 0), fill=COPPER_LIGHT, width=2)
        d.line((0, 30, 31, 30), fill=COPPER, width=2)
    return im


def wall(kind):
    im = Image.new('RGBA', (64, 64))
    d = ImageDraw.Draw(im)
    if 'h' in kind:
        d.polygon([(0,24),(32,24),(63,55),(63,63),(31,63),(0,32)], fill=LIMESTONE)
        d.line((0,24,32,24,63,55), fill=PALE, width=2)
        d.line((0,31,31,62,63,62), fill=JOINT, width=2)
        for k in (8, 24):
            d.line((k,26,k+29,55), fill=JOINT)
        d.line((3,30,31,58,63,58), fill=COPPER)
    if 'v' in kind:
        d.polygon([(24,0),(32,0),(63,31),(63,63),(55,63),(24,32)], fill=LIMESTONE)
        d.line((24,0,32,0,63,31), fill=PALE, width=2)
        for y in (8, 22, 31):
            d.line((25,y,55,y+30), fill=JOINT)
        d.line((32,4,62,34,62,62), fill=COPPER, width=2)
    if kind == 'post':
        d.polygon([(24,24),(32,24),(63,55),(63,63),(55,63),(24,32)], fill=COPPER)
        d.line((24,24,32,24,63,55), fill=COPPER_LIGHT, width=2)
        d.line((25,31,56,62,63,62), fill=DARK)
    if kind == 'hw':
        d.polygon([(12,29),(24,29),(42,47),(29,47)], fill=DARK)
        d.polygon([(15,31),(23,31),(38,46),(30,46)], fill=JADE)
        d.line((21,32,34,45), fill=JADE_LIGHT)
    if kind == 'vw':
        d.polygon([(28,10),(51,33),(51,50),(28,27)], fill=DARK)
        d.polygon([(30,14),(49,33),(49,46),(30,27)], fill=JADE)
        d.line((31,19,48,36), fill=JADE_LIGHT, width=2)
    return im


def fixture(size, sid, gems=False):
    w, h = {1: (32, 32), 2: (64, 64), '1x2': (32, 64)}[size]
    im = Image.new('RGBA', (w, h))
    d = ImageDraw.Draw(im)
    x, y = (w-32 if w == 32 else 25), h-32
    if size == '1x2':
        y -= 5
    x1, y1 = min(w-1, x+30), min(h-1, y+30)
    d.rounded_rectangle((x+1,y+1,x1,y1), radius=3, fill=DARK)
    d.rectangle((x+2,y+2,x1-3,y1-8), fill=JADE)
    d.line((x+3,y+3,x1-4,y+3), fill=JADE_LIGHT)
    d.rectangle((x+3,y1-7,x1-1,y1-3), fill=COPPER)
    d.line((x+3,y1-7,x1-2,y1-7), fill=COPPER_LIGHT)
    if gems:
        for u, color in zip((8, 15, 22), ('#83e5bd', '#f0a782', '#c5a1f2')):
            d.polygon(((u,y+5),(u+3,y+9),(u,y+14),(u-3,y+9)), fill=color)
            d.point((u-1,y+8), fill=PALE)
    else:
        d.rectangle((x+7,y+7,x1-7,y1-12), outline=JADE_LIGHT)
        for u in (x+6, x1-5):
            d.point((u,y1-5), fill=PALE)
        if sid in (1621, 1624, 1626):
            d.line((x+3,y+6,x+3,y1-8), fill=COPPER_LIGHT)
    return im


def trim(size, kind):
    w, h = {1: (32,32), '1x2': (32,64), '2x1': (64,32)}[size]
    im = Image.new('RGBA', (w, h))
    d = ImageDraw.Draw(im)
    if 'h' in kind:
        d.rectangle((max(0,w-35), h-8, w-1, h-1), fill=DARK)
        d.line((max(0,w-35),h-8,w-1,h-8), fill=COPPER_LIGHT, width=2)
    if 'v' in kind:
        d.polygon([(w-19,h-37),(w-14,h-38),(w-1,h-9),(w-1,h-1),(w-6,h-1),(w-19,h-31)], fill=DARK)
        d.line((w-18,h-34,w-3,h-3), fill=COPPER_LIGHT, width=2)
    return im


def stall_piece(kind):
    image = Image.new('RGBA', (32, 32))
    d = ImageDraw.Draw(image)
    if kind == 'side':
        d.rectangle((19,0,30,31), fill=DARK)
        d.rectangle((19,0,27,31), fill=JADE)
        d.line((19,0,19,31), fill=COPPER_LIGHT, width=2)
        for y in (4,19):
            d.rectangle((22,y,25,y+6), fill=JADE_LIGHT)
        return image
    d.rectangle((0,14,31,28), fill=DARK)
    d.rectangle((0,14,31,24), fill=LIMESTONE)
    d.line((0,14,31,14), fill=PALE, width=2)
    d.line((0,25,31,25), fill=COPPER)
    for x in (8,24):
        d.line((x,16,x,23), fill=JOINT)
    if kind == 'emblem':
        d.rounded_rectangle((3,0,28,24), radius=4, fill=DARK, outline=COPPER_LIGHT, width=2)
        d.polygon(((15,4),(23,11),(15,20),(8,11)), fill='#7ee2b5')
        d.polygon(((15,4),(16,11),(8,11)), fill='#c4fce0')
        d.polygon(((16,11),(23,11),(15,20)), fill=JADE)
    return image


def definitions():
    out = [(sid, 1794, 1, f'market {key} paving', floor(key)) for key, sid in FLOOR_IDS.items()]
    for proto, sid in REPLACEMENTS.items():
        if proto in WALLS:
            out.append((sid, proto, 2, 'limestone arcade masonry', wall(WALLS[proto])))
        elif proto in FURNITURE:
            size = FURNITURE[proto]
            out.append((sid, proto, size, 'jade and copper display', fixture(size, proto)))
        elif proto in ROOF_EDGES:
            out.append((sid, proto, 1, 'copper roof flashing', trim(1, ROOF_EDGES[proto])))
        else:
            size = RAILS[proto]
            out.append((sid, proto, size, 'copper terrace guard', trim(size, 'h' if proto == 1600 else 'v')))
    out += [
        (TONKA_COUNTER, 1622, 1, 'gem exchange counter', fixture(1, 1622, gems=True)),
        (TONKA_DIVIDER, 1623, 1, 'gem shop partition', stall_piece('wall')),
        (TONKA_CREST, 1623, 1, 'gem shop emblem', stall_piece('emblem')),
    ]
    for i, proto in enumerate((1621, 1620, 1620, 1620)):
        image = fixture('1x2', proto)
        d = ImageDraw.Draw(image)
        if i == 0:
            d.rounded_rectangle((10, 34, 21, 44), radius=2, fill=COPPER_LIGHT, outline=DARK)
            d.arc((12, 31, 19, 37), 180, 360, fill=COPPER_LIGHT)
        elif i == 1:
            for radius in (7, 5, 3):
                d.ellipse((16-radius,40-radius,16+radius,40+radius), outline=COPPER_LIGHT)
        else:
            d.line((9, 45, 21, 32), fill=COPPER_LIGHT, width=2)
            if i == 2:
                d.polygon(((7,42),(12,47),(7,49),(5,47)), fill=PALE)
            else:
                d.line((21,32,24,40,22,42), fill=PALE)
        out.append((SELLER_DISPLAY+i, proto, '1x2', 'seller equipment display', image))
    return out + [(TONKA_SIDE, 1623, 1, 'gem shop screen', stall_piece('side'))]


def items():
    return [dict(server_id=sid, client_id=CLIENT+sid-BASE, prototype=proto, tiles=size,
                 decor=True, fixed=True, png=f'seller_market_{sid}.png',
                 name=name, descr='A fixed furnishing of the Small Street market.',
                 **({'light': (4, 215)} if sid == TONKA_CREST else {}))
            for sid, proto, size, name, _ in definitions()]


if __name__ == '__main__':
    for sid, _, _, _, image in definitions():
        image.save(OUT / f'seller_market_{sid}.png')
