-- Dark Mage: rayo de sombra que drena vida (pack "shadow").
-- Hechizo rápido y flojo; el Dark Mage encadena varios por segundo.
attackType = ATTACK_LIFEDRAIN
animationEffect = NM_ANI_SHADOWBALL

hitEffect = NM_ME_NONE
damageEffect = NM_ME_SHADOW_HIT
animationColor = BLACK
offensive = true
drawblood = false

DarkMageBolt = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
DarkMageBolt.minDmg = 35
DarkMageBolt.maxDmg = 70

return doTargetMagic(cid, centerpos, DarkMageBolt:ordered())
end
