-- Orc Berserker Pot Thrower: tira pots (trough 1775) alrededor del objetivo.
-- El pot es blockSolid: no deja pasar por encima mientras dura.
-- Tiles con criatura o bloqueados se saltean solos (misma regla que magic wall),
-- por eso el area 3x3 nunca crea el item bajo el jugador.
area = {
 {1, 1, 1},
 {1, 1, 1},
 {1, 1, 1}
 }

attackType = ATTACK_NONE
needDirection = false
areaEffect = NM_ME_PUFF
animationEffect = NM_ANI_LARGEROCK

hitEffect = NM_ME_PUFF
damageEffect = NM_ME_NONE
animationColor = RED
offensive = true
drawblood = false

PotObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

-- 10s real: DECAY_INTERVAL es 5000ms; valores no multiplo de ese interval se redondean.
durationTicks = 10000
itemid = 1775

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}

return doAreaGroundMagic(cid, centerpos, needDirection, areaEffect, area, PotObject:ordered(),
	0, durationTicks, itemid, 1)
end
