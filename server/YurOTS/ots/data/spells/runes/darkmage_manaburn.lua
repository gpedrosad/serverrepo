-- Dark Mage: quema de maná.
-- Hechizo rápido y flojo; el Dark Mage encadena varios por segundo.
attackType = ATTACK_MANADRAIN
animationEffect = NM_ANI_SUDDENDEATH

hitEffect = NM_ME_NONE
damageEffect = NM_ME_LOOSE_ENERGY
animationColor = DARK_BLUE
offensive = true
drawblood = false

DarkMageBolt = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
DarkMageBolt.minDmg = 40
DarkMageBolt.maxDmg = 80

return doTargetMagic(cid, centerpos, DarkMageBolt:ordered())
end
