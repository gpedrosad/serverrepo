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
TONKA_WORKTOP = TONKA_SIDE + 1
TONKA_RAIL = TONKA_WORKTOP + 1

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
        d.polygon(((8,25),(22,25),(26,30),(12,30)), fill='#566359', outline=DARK)
        d.rectangle((10,10,21,25), fill=LIMESTONE, outline=DARK)
        d.rectangle((11,13,16,23), fill=PALE)
        d.rectangle((9,22,22,24), fill=COPPER)
        d.rectangle((8,6,22,15), fill=DARK)
        d.rectangle((10,8,20,12), fill='#bf8239')
        d.rectangle((12,9,18,11), fill='#ffe6a5')
        d.line((10,7,20,7), fill=COPPER_LIGHT)
        d.polygon(((7,6),(12,2),(18,2),(24,6)), fill=JADE, outline=DARK)
        d.line((12,3,17,3), fill=JADE_LIGHT)
        return image
    if kind == 'rail':
        d.rectangle((10,0,23,31), fill=DARK)
        d.rectangle((11,0,19,31), fill=JADE)
        d.line((11,0,11,31), fill=JADE_LIGHT)
        d.line((19,0,19,31), fill=COPPER)
        for y in (1, 16, 29):
            d.line((10,y,23,y), fill=COPPER_LIGHT, width=2)
        return image
    d.rectangle((0,8,31,28), fill=DARK)
    d.rectangle((0,9,31,24), fill=LIMESTONE)
    d.line((0,9,31,9), fill=PALE)
    for row, y in enumerate((11, 17, 23)):
        d.line((0,y,31,y), fill=JOINT)
        for x in range(5 + 6*(row % 2), 32, 12):
            d.line((x,y,x,y+4), fill=JOINT)
    d.rectangle((0,24,31,28), fill=JADE)
    d.line((0,24,31,24), fill=COPPER_LIGHT)
    if kind == 'emblem':
        d.polygon(((3,5),(9,1),(22,1),(28,5),(28,20),(15,25),(3,20)),
                  fill=DARK, outline=COPPER_LIGHT)
        d.polygon(((10,6),(20,6),(24,11),(15,20),(7,11)), fill='#5e9a87')
        d.polygon(((10,6),(20,6),(17,11),(7,11)), fill='#d3f2cc')
        d.polygon(((17,11),(24,11),(15,20)), fill='#36635e')
    return image


def tonka_worktops():
    """Draw one two-square jeweler's counter, then slice it at the join."""
    image = Image.new('RGBA', (64, 32))
    d = ImageDraw.Draw(image)
    d.polygon(((3,25),(60,25),(63,29),(7,29)), fill='#5c6357')
    d.rectangle((5,9,58,27), fill=DARK)
    d.rectangle((7,16,56,25), fill='#526358')
    for x in (7, 31, 54):
        d.rectangle((x,19,x+3,28), fill=JADE, outline=DARK)
        d.point((x+1,22), fill=COPPER_LIGHT)
    d.polygon(((2,7),(56,7),(61,11),(61,20),(3,20),(1,17)), fill=JOINT)
    d.polygon(((3,7),(56,7),(59,10),(59,17),(3,17)), fill='#decfae')
    d.line((4,8,55,8), fill='#f6eaca')
    d.line((4,19,58,19), fill=COPPER_LIGHT)
    d.rectangle((34,9,54,16), fill='#663e58')
    d.line((35,9,53,9), fill='#9d667e')
    for x, color, light in ((39,'#52a380','#cbf9d2'), (44,'#af5b6e','#f1a9a2'),
                            (50,'#716aae','#c4bbea')):
        d.polygon(((x,9),(x+3,12),(x,16),(x-3,12)), fill=DARK)
        d.polygon(((x,10),(x+2,12),(x,15),(x-2,12)), fill=color)
        d.point((x-1,11), fill=light)
    # Scale and open ledger on the work side.
    d.line((11,11,24,11), fill='#766144')
    d.line((17,9,17,15), fill=COPPER)
    d.ellipse((9,12,14,14), fill=COPPER_LIGHT, outline=COPPER)
    d.ellipse((21,12,26,14), fill=COPPER_LIGHT, outline=COPPER)
    d.rectangle((28,10,32,15), fill=PALE, outline=JOINT)
    return image.crop((0,0,32,32)), image.crop((32,0,64,32))


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
    worktop, display = tonka_worktops()
    out += [
        (TONKA_COUNTER, 1622, 1, 'gem exchange counter', display),
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
    return out + [
        (TONKA_SIDE, 1623, 1, 'gem shop lantern post', stall_piece('side')),
        (TONKA_WORKTOP, 1622, 1, 'gem shop worktop', worktop),
        (TONKA_RAIL, 1623, 1, 'gem shop side rail', stall_piece('rail')),
    ]


def items():
    return [dict(server_id=sid, client_id=CLIENT+sid-BASE, prototype=proto, tiles=size,
                 decor=True, fixed=True, png=f'seller_market_{sid}.png',
                 name=name, descr='A fixed furnishing of the Small Street market.',
                 **({'light': (4, 215)} if sid in (TONKA_CREST, TONKA_SIDE) else {}))
            for sid, proto, size, name, _ in definitions()]


if __name__ == '__main__':
    for sid, _, _, _, image in definitions():
        image.save(OUT / f'seller_market_{sid}.png')
