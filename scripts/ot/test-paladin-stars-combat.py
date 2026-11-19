#!/usr/bin/env python3
"""Combate de stars contra personajes sintéticos del fixture, nunca contra 7171.

Fixture: Star Gale/Venom/Storm/Royal/Forbidden en 2000,2000,7; Star Target en
2004,2000,7, cuenta 111111/asantest. Sin equipo protector y con 30000 HP/MP.
Captura paquetes enmarcados del protocolo 7.6 y busca efectos con posiciones exactas.
"""
import argparse
import re
import select
import socket
import statistics
import struct
import time


def string(value):
    raw = value.encode('latin-1')
    return struct.pack('<H', len(raw)) + raw


def pos(x, y, z=7):
    return struct.pack('<HHB', x, y, z)


class Client:
    def __init__(self, host, port, name):
        self.name, self.buffer, self.packets, self.ids = name, b'', [], {}
        self.position = None
        self.sock = socket.create_connection((host, port), timeout=10)
        self.sock.setblocking(False)
        self.send(struct.pack('<HBHB', 0x020A, 2, 760, 0) + struct.pack('<I', 111111)
                  + string(name) + string('asantest'))

    def send(self, data):
        self.sock.sendall(struct.pack('<H', len(data)) + data)

    def read(self):
        chunk = self.sock.recv(65536)
        if not chunk:
            raise RuntimeError(f'{self.name}: conexión cerrada')
        self.buffer += chunk
        while len(self.buffer) >= 2:
            size = struct.unpack_from('<H', self.buffer)[0]
            if len(self.buffer) < size + 2:
                break
            data, self.buffer = self.buffer[2:size+2], self.buffer[size+2:]
            if data[:1] == b'\x14':
                raise RuntimeError(f'{self.name}: login rechazado {data!r}')
            self.packets.append((time.monotonic(), data))
            if len(data)>=14 and data[0]==10 and data[8]==100:
                self.position=data[9:14]
            for m in re.finditer(rb'\x61\x00....(....)([\x01-\x1e])\x00([A-Za-z ]{1,30})', data, re.S):
                self.ids[m[3][:m[2][0]].decode()] = struct.unpack('<I', m[1])[0]

    def count(self, pattern):
        return sum(data.count(pattern) for _, data in self.packets)

    def stats(self):
        out = []
        for stamp, data in self.packets:
            for m in re.finditer(b'\xa0(..)\x30\x75', data, re.S):
                hp = struct.unpack('<H', m[1])[0]
                start = m.start()
                if start + 19 <= len(data):
                    mana, maxmana = struct.unpack_from('<HH', data, start+14)
                    if maxmana == 30000:
                        out.append((stamp, hp, mana))
        return out


def pump(clients, seconds):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        ready, _, _ = select.select([c.sock for c in clients], [], [], min(.1, max(0, until-time.monotonic())))
        for client in clients:
            if client.sock in ready:
                client.read()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--host', default='192.168.1.17')
    ap.add_argument('--port', type=int, default=7279)
    ap.add_argument('--guards-only', action='store_true')
    ap.add_argument('--quick', action='store_true', help='solo Gale, Royal y rechazo de knight')
    args = ap.parse_args()
    if args.port == 7171:
        ap.error('Prohibido usar el servidor donde se juega')
    if args.guards_only:
        for name, missile in [('Star Venom',20),('Star Storm',21)]:
            for target_name,y in [('Star Immune',2002),('Star Trainer',2003)]:
                actor=Client(args.host,args.port,name)
                deadline=time.monotonic()+10
                while target_name not in actor.ids and time.monotonic()<deadline:
                    pump([actor],.2)
                assert target_name in actor.ids,(name,actor.ids)
                shot=re.compile(re.escape(b'\x85'+actor.position)+b'.{5}'+bytes([missile]),re.S)
                def shots():
                    return sum(len(shot.findall(data)) for _,data in actor.packets)
                def effects(effect):
                    return sum(1 for _,data in actor.packets for m in re.finditer(b'\x83(.{5})'+re.escape(bytes([effect])),data,re.S)
                               if 1990<=struct.unpack('<HHB',m[1])[0]<=2020 and 1990<=struct.unpack('<HHB',m[1])[1]<=2020 and m[1][-1]==7)
                actor.packets.clear()
                actor.send(b'\xa1'+struct.pack('<I',actor.ids[target_name]))
                deadline=time.monotonic()+25
                while shots()<12 and time.monotonic()<deadline:
                    pump([actor],.1)
                actor.send(b'\xa1'+struct.pack('<I',0))
                assert shots()>=12,(target_name,shots())
                assert effects(46 if missile==20 else 47)==0
                assert effects(17)==0
                print(f'PASS: {name} vs {target_name}, 12 tiros sin proc elemental',flush=True)
                actor.sock.close()
                time.sleep(.5)
        return
    target = Client(args.host, args.port, 'Star Target')
    pump([target], 1)
    for name, missile, interval, effect in [('Star Gale',19,.9,45),('Star Royal',19,.9,45),
                                           ('Star Venom',20,1.333,46),('Star Storm',21,1.5,47),
                                           ('Star Forbidden',19,.9,None)]:
        if args.quick and name in ('Star Venom','Star Storm'):
            continue
        actor = Client(args.host, args.port, name)
        clients = [actor,target]
        login_deadline=time.monotonic()+10
        while 'Star Target' not in actor.ids and time.monotonic()<login_deadline:
            pump(clients,.2)
        assert 'Star Target' in actor.ids, (name, actor.ids)
        shot = b'\x85' + actor.position + pos(2004,2000) + bytes([missile])
        hit = b'\x83' + pos(2004,2000) + bytes([effect or 45])
        if name == 'Star Storm':
            target.send(b'\x96\x01' + string('utamo vita'))
            pump(clients, 1)
            hp_before, mana_before = target.stats()[-1][1:]
        actor.send(b'\xa1' + struct.pack('<I', actor.ids['Star Target']))
        start = time.monotonic()
        while time.monotonic()-start < (3 if effect is None else 55):
            pump(clients,.1)
            if effect is None:
                if any(b'Only paladins and royal paladins' in data for _,data in actor.packets):
                    break
            elif actor.count(shot) >= (4 if name=='Star Royal' else 9) and actor.count(hit)>0:
                break
        actor.send(b'\xa1' + struct.pack('<I',0))
        pump(clients,.5)
        if effect is None:
            assert actor.count(shot)==0
            assert any(b'Only paladins and royal paladins' in data for _,data in actor.packets)
            print('PASS: knight rechazado, sin proyectiles ni ataque', flush=True)
        else:
            stamps = [stamp for stamp,data in actor.packets for _ in range(data.count(shot))]
            assert len(stamps)>=4 and actor.count(hit)>0, (name,len(stamps),actor.count(hit))
            median = statistics.median(b-a for a,b in zip(stamps,stamps[1:]))
            assert abs(median-interval)<.22, (name,median,interval)
            print(f'PASS: {name}, {len(stamps)} tiros, intervalo {median:.3f}s, efectos {actor.count(hit)}',flush=True)
            if name=='Star Venom':
                ticks = target.count(b'\x83'+pos(2004,2000)+b'\x11')
                pump(clients,9)
                new_ticks=target.count(b'\x83'+pos(2004,2000)+b'\x11')-ticks
                assert 1<=new_ticks<=4, new_ticks
                print(f'PASS: veneno sigue después de cancelar ataque ({new_ticks} ticks restantes)',flush=True)
            if name=='Star Storm':
                hp_after,mana_after=target.stats()[-1][1:]
                assert hp_after>=hp_before and mana_after<mana_before,(hp_before,hp_after,mana_before,mana_after)
                print('PASS: descarga con maná shield drena maná y conserva HP',flush=True)
        actor.send(b'\x14')
        pump([target],.4)
        actor.sock.close()
    target.send(b'\x14')
    target.sock.close()


if __name__=='__main__':
    main()
