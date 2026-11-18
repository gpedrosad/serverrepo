-- Dark Mage: esquirla de hielo (pack "ice"; el motor no tiene daño de hielo: es físico con número celeste).
-- Hechizo rápido y flojo; el Dark Mage encadena varios por segundo.
attackType = ATTACK_PHYSICAL
animationEffect = NM_ANI_FROSTBALL

hitEffect = NM_ME_NONE
damageEffect = NM_ME_ICE_SHATTER
animationColor = LIGHT_BLUE
offensive = true
drawblood = false

DarkMageBolt = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
DarkMageBolt.minDmg = 30
DarkMageBolt.maxDmg = 65

return doTargetMagic(cid, centerpos, DarkMageBolt:ordered())
end
