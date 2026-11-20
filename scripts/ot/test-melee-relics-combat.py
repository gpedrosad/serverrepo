#!/usr/bin/env python3
"""Combate contra el fixture sintético de MELEE_RELICS.md, nunca contra 7171."""
import argparse
import importlib.util
from pathlib import Path
import re
import struct
import time

spec=importlib.util.spec_from_file_location('star_qa',Path(__file__).with_name('test-paladin-stars-combat.py'))
qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--host',default='192.168.1.17');ap.add_argument('--port',type=int,default=7281)
    ap.add_argument('--guards-only',action='store_true')
    args=ap.parse_args()
    if args.port==7171:ap.error('Prohibido probar sobre el servidor de juego')
    def login(name):
        c=qa.Client(args.host,args.port,name)
        deadline=time.monotonic()+6
        while not c.stats() and time.monotonic()<deadline:qa.pump([c],.2)
        assert c.stats(),(name,'no stats after login')
        return c
    def attack(actor,target_name,clients):
        deadline=time.monotonic()+5
        while target_name not in actor.ids and time.monotonic()<deadline:qa.pump(clients,.1)
        assert target_name in actor.ids,(target_name,actor.ids)
        actor.packets.clear()
        actor.send(b'\xa1'+struct.pack('<I',actor.ids[target_name]))
    def stop(actor,clients):
        actor.send(b'\xa1'+struct.pack('<I',0));qa.pump(clients,.2)
    def effects(actor,position,effect):
        return actor.count(b'\x83'+position+bytes([effect]))
    def damage_events(actor,position):
        pattern=re.compile(re.escape(b'\x84'+position)+b'.([\x01-\x06])\x00([0-9]{1,6})',re.S)
        return [(stamp,int(m[2])) for stamp,data in actor.packets for m in pattern.finditer(data)
                if len(m[2])==m[1][0]]
    target=login('Relic Target');target_pos=qa.pos(2001,2000)
    cases=[] if args.guards_only else [('Relic Sword',48,2),('Relic Elite',48,2),('Relic Axe',49,3),('Relic Club',50,2)]
    for name,effect,minimum in cases:
        actor=login(name);clients=[actor,target];qa.pump(clients,.4)
        before_mana=actor.stats()[-1][2];attack(actor,'Relic Target',clients)
        deadline=time.monotonic()+45
        while (effects(actor,actor.position if effect==49 else target_pos,effect)<minimum or
               len(damage_events(actor,target_pos))<8) and time.monotonic()<deadline:qa.pump(clients,.1)
        stop(actor,clients)
        hits=damage_events(actor,target_pos);n=effects(actor,actor.position if effect==49 else target_pos,effect)
        assert len(hits)>=8 and n>=minimum,(name,len(hits),n,actor.stats())
        if effect==48:
            # Each dimensional cut must consume three consecutive successful hits.
            combo=0
            for _,data in actor.packets:
                if b'\x83'+target_pos+b'\x03' in data:combo=0
                packet_hits=len(damage_events(type('Packet',(),{'packets':[(0,data)]})(),target_pos))
                combo+=packet_hits
                if b'\x83'+target_pos+b'\x30' in data:
                    assert combo==3,(name,combo);combo=0
            assert n<=len(hits)//3
        if effect==49:
            values=[s[2] for s in actor.stats()]
            assert values[-1]>before_mana,(before_mana,values)
            assert all(0<=b-a<=5 for a,b in zip([before_mana]+values,values))
            target.send(b'\x96\x01'+qa.string('utamo vita'));qa.pump(clients,1)
            assert any(b'\xa2' in data for _,data in target.packets), 'no icon packet'
            hp,mana=target.stats()[-1][1:];own_mana=actor.stats()[-1][2]
            attack(actor,'Relic Target',clients);qa.pump(clients,6);stop(actor,clients)
            assert target.stats()[-1][1]==hp and target.stats()[-1][2]<mana
            assert (not actor.stats() or actor.stats()[-1][2]==own_mana) and effects(actor,actor.position,49)==0
            print('PASS: Aethercleaver vs mana shield, no health loss / no mana gain',flush=True)
        print(f'PASS: {name}, {len(hits)} hits, {n} custom effects',flush=True)
        actor.sock.close();qa.pump([target],.3)
    target.sock.close()
    for name,monster,z in [('Relic Immune Sword','Relic Immune',8),
                           ('Relic Trainer Sword','Relic Trainer',9),
                           ('Relic Trainer Axe','Relic Trainer',9),
                           ('Relic Trainer Club','Relic Trainer',9)]:
        actor=login(name);attack(actor,monster,[actor]);qa.pump([actor],12);stop(actor,[actor])
        assert len(damage_events(actor,qa.pos(2001,2000,z)))>=5,(name,actor.ids)
        for effect in [48,49,50]:
            assert effects(actor,qa.pos(2001,2000,z),effect)==0 and effects(actor,actor.position,effect)==0,name
        print(f'PASS: {name} vs {monster}, no special effects',flush=True);actor.sock.close()
    for name,effect in [('Relic Tank Axe',49),('Relic Tank Club',50)]:
        actor=login(name);before=actor.stats()[-1][2];attack(actor,'Relic Tank',[actor])
        deadline=time.monotonic()+45
        position=actor.position if effect==49 else qa.pos(2001,2000,10)
        while (effects(actor,position,effect)<2 or len(damage_events(actor,qa.pos(2001,2000,10)))<8) and time.monotonic()<deadline:qa.pump([actor],.1)
        stop(actor,[actor]);assert effects(actor,position,effect)>=2
        if effect==49:
            values=[s[2] for s in actor.stats()];assert values[-1]>before
            assert all(0<=b-a<=10 for a,b in zip([before]+values,values))
        print(f'PASS: {name} vs armored monster, {effects(actor,position,effect)} procs',flush=True);actor.sock.close()
    print('MELEE_RELICS_COMBAT_PASS',flush=True)


if __name__=='__main__':main()
