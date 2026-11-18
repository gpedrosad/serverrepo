-- Dark Mage: chispa de energía.
-- Hechizo rápido y flojo; el Dark Mage encadena varios por segundo.
attackType = ATTACK_ENERGY
animationEffect = NM_ANI_ENERGY

hitEffect = NM_ME_NONE
damageEffect = NM_ME_ENERGY_DAMAGE
animationColor = ENERGY
offensive = true
drawblood = false

DarkMageBolt = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
DarkMageBolt.minDmg = 30
DarkMageBolt.maxDmg = 60

return doTargetMagic(cid, centerpos, DarkMageBolt:ordered())
end
