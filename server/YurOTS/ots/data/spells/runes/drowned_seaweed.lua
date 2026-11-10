-- Drowned Sailor: tira un manojo de algas mojadas (proyectil verde) que pega veneno con salpicadura de agua y,
-- si pega, deja al objetivo quieto 1 segundo (la misma raíz de la Anchor Rune, sin paralyze).
attackType = ATTACK_POISON
animationEffect = NM_ANI_FLYPOISONFIELD

hitEffect = NM_ME_NONE
damageEffect = NM_ME_LOOSE_ENERGY
animationColor = GREEN
offensive = true
drawblood = false

SeaweedObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
SeaweedObject.minDmg = 25
SeaweedObject.maxDmg = 55

local hit = doTargetMagic(cid, centerpos, SeaweedObject:ordered())
if hit then
	doAnchorRoot(cid, centerpos)
end
return hit
end
