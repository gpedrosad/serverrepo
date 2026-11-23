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
COUNTER_NORTH = TONKA_SIDE + 1
COUNTER_SOUTH = COUNTER_NORTH + 1

STONE = '#92816a'
PALE = '#c7b390'
JOINT = '#544739'
COPPER = '#806047'
COPPER_LIGHT = '#d8aa70'
CLOTH = '#633c45'
DARK = '#38291f'
OAK = ('#71452a', '#976537', '#b58248', '#c99655', '#dfae69')


def grain(x, y, seed=0):
    """Stable texture for hand-cut stone and timber, with no random seed state."""
    return (x * 47 + y * 83 + x * y * 17 + seed * 109) % 31


def floor(key):
    colors = {
        'arcade': ('#4a493d', '#6e6b5a', '#898472', '#a79e83'),
        'seller': ('#61584b', '#8a8070', '#a1957e', '#b4a891'),
        'house': ('#634025', '#895530', '#a67140', '#c68e51'),
        'gallery': ('#4d4944', '#716b63', '#898276', '#a39a8b'),
        'terrace': ('#59574c', '#7c7969', '#938e78', '#b4ab8f'),
        'roof': ('#542b20', '#86412c', '#a75838', '#c2774b'),
        'tonka': ('#634025', '#926037', '#aa7546', '#c49157'),
        'threshold': ('#554c3f', '#7e7159', '#998a70', '#b49e76'),
    }
    shadow, body, mid, light = colors[key]
    image = Image.new('RGBA', (32, 32), shadow)
    d = ImageDraw.Draw(image)
    if key in ('house', 'tonka'):
        for y in range(0, 32, 8):
            seam = (9 + y * 3) % 27
            fill = body if y in (0, 24) else mid
            d.rectangle((0, y, 31, y+6), fill=fill)
            d.line((0, y, 31, y), fill=light)
            d.line((seam, y+1, seam, y+6), fill=shadow)
            for x in range(2, 29, 5):
                yy = y + 2 + grain(x,y) % 4
                if abs(x-seam) > 2:
                    d.line((x, yy, x+2, yy), fill=body if fill == mid else mid)
            for x in (seam-2, seam+2):
                if 0 <= x < 32:
                    d.point((x, y+3), fill=shadow)
        return image
    if key == 'roof':
        for y in range(0, 32, 8):
            for x in range(-8 if y % 16 else 0, 32, 8):
                d.polygon(((x+1,y),(x+5,y),(x+7,y+2),(x+7,y+6),(x+1,y+6),(x,y+5)), fill=body)
                d.line((x+1,y+1,x+5,y+1), fill=light)
                d.line((x+2,y+2,x+2,y+5), fill=mid)
        return image
    for row, y in enumerate((0, 8, 16, 24)):
        x = -6 if row in (1, 3) else 0
        while x < 32:
            width = (11, 15, 13)[grain(x, y) % 3]
            d.polygon(((x+1,y+1),(x+width-2,y+1),(x+width-1,y+2),(x+width-1,y+5),
                       (x+width-3,y+7),(x+2,y+7),(x,y+5),(x,y+3)), fill=body)
            d.line((x+2,y+1,x+width-3,y+1), fill=light)
            d.line((x+2,y+2,x+width-4,y+2), fill=mid)
            for u in range(x+2, x+width-2):
                if grain(u,y) % 3 == 0:
                    d.point((u, y+3+grain(u,y+4)%3), fill=mid)
            d.line((x+3,y+6,x+width-4,y+6), fill=shadow)
            x += width + 1
    return image


def wall(kind):
    image = Image.new('RGBA', (64, 64))
    d = ImageDraw.Draw(image)
    tones = ('#6e5e4d', '#887765', '#a39177', '#af9b80', '#c0ad8c')
    if 'h' in kind:
        for depth in range(32):
            for u in range(32):
                x, y = u+depth, 24+depth
                brick = (u + 6*(depth//8 % 2)) % 12
                window = 'w' in kind and 9 < u < 22 and 7 < depth < 23
                if window:
                    fill = ('#b69a6c' if u in (10,21) or depth in (8,22) else
                            '#5a685e' if u in (15,16) or depth == 16 else '#293a39')
                elif depth % 8 == 7 or brick == 0:
                    fill = JOINT
                else:
                    fill = tones[2 + (grain(u//3,depth)%3 if depth%8 < 2 else grain(u,depth)%2)]
                if x < 64:
                    d.point((x,y), fill=fill)
        d.line((0,24,31,24,63,56), fill=PALE)
        d.line((0,32,31,63,63,63), fill=DARK)
    if 'v' in kind:
        for u in range(32):
            x = 32+u
            for height in range(32):
                y = u+height
                brick = (u + 6*(height//8 % 2)) % 13
                window = 'w' in kind and 6 <= u <= 23 and 5 <= height <= 24
                if window:
                    fill = ('#bb9e70' if u in (6,23) or height in (5,24) else
                            '#65736b' if u in (14,15) or height == 14 else '#283633')
                elif height % 8 == 7 or brick == 0:
                    fill = JOINT
                else:
                    fill = tones[1 + (grain(u,height//2)%3 if height%8 < 3 else grain(u,height)%2)]
                d.point((x,y), fill=fill)
            for j in range(8):
                d.point((x-j,u), fill=tones[3+(j%3==0)])
        d.line((24,0,32,0,63,31), fill=PALE)
        d.line((32,31,63,62), fill=DARK)
    if kind == 'post':
        d.polygon([(24,24),(32,24),(63,55),(63,63),(55,63),(24,32)], fill=tones[1])
        d.line((24,24,32,24,63,55), fill=PALE, width=2)
        d.line((25,31,56,62,63,62), fill=DARK)
        for k in (8, 17, 26):
            d.line((24+k,27+k,31+k,27+k), fill=JOINT)
    return image


def counter_run(end=None):
    """Oak rail with aligned edges and two capped ends for Seller's counter."""
    image = Image.new('RGBA', (32, 32))
    d = ImageDraw.Draw(image)
    y0, y1 = (3 if end == 'north' else 0), (28 if end == 'south' else 31)
    d.rectangle((3, y0, 30, y1), fill=DARK)
    d.rectangle((4, y0, 24, y1), fill=OAK[2])
    d.line((4, y0, 4, y1), fill=OAK[4])
    d.line((24, y0, 24, y1), fill=OAK[4])
    d.rectangle((25, y0+1, 28, y1-1), fill=OAK[0])
    d.line((29, y0, 29, y1), fill=OAK[1])
    for x in range(5, 24):
        for y in range(y0, y1+1):
            g = grain(x,y//3)
            fill = OAK[1] if x in (10,17,23) or g < 3 else OAK[3] if g > 25 else OAK[2]
            d.point((x,y), fill=fill)
    for y in (y0+3, y1-3):
        d.rectangle((26, y, 28, y+2), fill=COPPER)
        d.point((27, y), fill=COPPER_LIGHT)
    if end == 'north':
        d.line((5,y0,25,y0), fill=OAK[4], width=2)
    elif end == 'south':
        d.line((4,y1-5,24,y1-5), fill=OAK[4])
        d.rectangle((5,y1-4,28,y1-1), fill=OAK[0])
        d.point((7,y1-2), fill=COPPER_LIGHT)
        d.point((26,y1-2), fill=COPPER_LIGHT)
    return image


def fixture(size, sid, gems=False):
    """Oak worktops, visible front panels and shaded legs in the original footprint."""
    if sid == 1622 and not gems:
        return counter_run()
    w, h = {1: (32,32), 2: (64,64), '1x2': (32,64)}[size]
    image = Image.new('RGBA', (w,h))
    d = ImageDraw.Draw(image)
    # The long side runs north–south for the shop row and east–west at the display ends.
    vertical = sid in (1620,1621,1622,1624,1628)
    x0 = 25 if size == 2 else 2
    y0 = 27 if size != 1 else 1
    x1 = min(w-2, x0+29)
    y1 = h-1
    if size == 1 and not vertical:
        x0, x1, y0, y1 = 0, 31, 6, 30
    if gems:
        y0, y1 = 4, 29
    depth = 6
    top = y1-depth
    d.polygon(((x0,y0),(x1-4,y0),(x1,y0+4),(x1,top),(x1-2,y1),
               (x0+3,y1),(x0,top)), fill=DARK)
    d.polygon(((x0+1,y0+1),(x1-4,y0+1),(x1-1,y0+4),(x1-1,top-1),
               (x0+1,top-1)), fill=OAK[2])
    for y in range(y0+2,top-1):
        for x in range(x0+2,x1-1):
            if y < y0+5 and x >= x1-4+y-y0:
                continue
            strip = x-x0 if vertical else y-y0
            xgrain = y if vertical else x
            g = grain(strip,xgrain//3,sid)
            color = (OAK[0] if strip % 7 == 0 and x >= x0+3 else OAK[3] if strip % 7 == 1
                     else OAK[2+(g>24)] if g>4 else OAK[1])
            d.point((x,y), fill=color)
    d.line((x0+2,y0+1,x1-5,y0+1), fill=OAK[4])
    d.line((x0+1,top,x1-1,top), fill=OAK[4])
    d.rectangle((x0+2,top+1,x1-2,y1-1), fill=OAK[0])
    for u in (x0+4, x1-4):
        d.rectangle((u-1,top+1,u+1,y1), fill=OAK[1])
        d.point((u,top+2), fill=COPPER_LIGHT)
    if gems:
        d.polygon(((5,8),(23,8),(27,19),(7,20)), fill=CLOTH, outline='#4d2836')
        d.line((6,9,22,9), fill='#986373')
        for x, y, base, glint in ((10,13,'#58977b','#bce8b7'), (16,12,'#ae504e','#ffb989'),
                                   (22,15,'#7663a9','#cdb0ed')):
            d.polygon(((x,y-3),(x+3,y),(x,y+3),(x-3,y)), fill=DARK)
            d.polygon(((x,y-2),(x+2,y),(x,y+2),(x-2,y)), fill=base)
            d.point((x-1,y-1), fill=glint)
    return image


def trim(size, kind):
    w, h = {1: (32,32), '1x2': (32,64), '2x1': (64,32)}[size]
    image = Image.new('RGBA', (w,h))
    d = ImageDraw.Draw(image)
    if 'h' in kind:
        x = max(0,w-35)
        d.rectangle((x,h-8,w-1,h-1), fill=DARK)
        d.line((x,h-7,w-1,h-7), fill=COPPER_LIGHT)
        d.line((x,h-6,w-1,h-6), fill=OAK[1])
        for xx in range(x+3,w,11):
            d.line((xx,h-5,xx,h-1), fill=OAK[0], width=2)
    if 'v' in kind:
        d.polygon([(w-19,h-37),(w-14,h-38),(w-1,h-9),(w-1,h-1),(w-6,h-1),(w-19,h-31)], fill=DARK)
        d.line((w-18,h-34,w-3,h-3), fill=OAK[1], width=2)
        d.line((w-18,h-36,w-3,h-5), fill=COPPER_LIGHT)
    return image


def stall_piece(kind):
    image = Image.new('RGBA', (32,32))
    d = ImageDraw.Draw(image)
    if kind == 'side':
        d.rectangle((19,0,30,31), fill=DARK)
        d.rectangle((20,0,27,31), fill=OAK[1])
        d.line((20,0,20,31), fill=OAK[3], width=2)
        for y in (3,17):
            d.rectangle((22,y,27,y+3), fill='#504747')
            d.point((24,y+1), fill=COPPER_LIGHT)
        return image
    d.rectangle((0,13,31,28), fill=JOINT)
    for row,y in enumerate((14,21)):
        for x in range(-5 if row else 0,32,10):
            d.rectangle((x,y,x+8,y+5), fill=STONE)
            d.line((x,y,x+7,y), fill=PALE)
            d.point((x+4,y+2), fill='#a48e74')
    d.line((0,27,31,27), fill=DARK)
    if kind == 'emblem':
        d.polygon(((4,0),(26,0),(29,6),(27,21),(16,26),(4,20),(2,6)), fill=DARK)
        d.polygon(((6,1),(24,1),(27,7),(25,20),(16,23),(6,19),(4,7)), fill=CLOTH, outline=COPPER_LIGHT)
        d.polygon(((15,5),(22,11),(15,19),(8,11)), fill='#619b72')
        d.polygon(((15,5),(16,11),(8,11)), fill='#c4ecc5')
        d.polygon(((16,11),(22,11),(15,19)), fill='#426c5a')
    return image


def definitions():
    out = [(sid, 1794, 1, f'market {key} flooring', floor(key)) for key, sid in FLOOR_IDS.items()]
    for proto, sid in REPLACEMENTS.items():
        if proto in WALLS:
            out.append((sid, proto, 2, 'market fieldstone masonry', wall(WALLS[proto])))
        elif proto in FURNITURE:
            size = FURNITURE[proto]
            out.append((sid, proto, size, 'oak shop counter', fixture(size, proto)))
        elif proto in ROOF_EDGES:
            out.append((sid, proto, 1, 'timber roof flashing', trim(1, ROOF_EDGES[proto])))
        else:
            size = RAILS[proto]
            out.append((sid, proto, size, 'bound oak railing', trim(size, 'h' if proto == 1600 else 'v')))
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
    return out + [
        (TONKA_SIDE, 1623, 1, 'gem shop screen', stall_piece('side')),
        (COUNTER_NORTH, 1622, 1, 'oak shop counter', counter_run('north')),
        (COUNTER_SOUTH, 1622, 1, 'oak shop counter', counter_run('south')),
    ]


def items():
    return [dict(server_id=sid, client_id=CLIENT+sid-BASE, prototype=proto, tiles=size,
                 decor=True, fixed=True, png=f'seller_market_{sid}.png',
                 name=name, descr='A fixed furnishing of the Small Street market.',
                 **({'light': (4, 215)} if sid == TONKA_CREST else {}))
            for sid, proto, size, name, _ in definitions()]


if __name__ == '__main__':
    for sid, _, _, _, image in definitions():
        image.save(OUT / f'seller_market_{sid}.png')
