-- Dark Mage: bola de veneno.
-- Hechizo rápido y flojo; el Dark Mage encadena varios por segundo.
attackType = ATTACK_POISON
animationEffect = NM_ANI_FLYPOISONFIELD

hitEffect = NM_ME_NONE
damageEffect = NM_ME_POISEN_RINGS
animationColor = GREEN
offensive = true
drawblood = false

DarkMageBolt = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
DarkMageBolt.minDmg = 25
DarkMageBolt.maxDmg = 50

return doTargetMagic(cid, centerpos, DarkMageBolt:ordered())
end
