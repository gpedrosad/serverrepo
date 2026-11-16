-- Bog Raider: se cura 65-95 (como en 8.60), con el brillo azul de las curas.
attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_NONE
damageEffect = NM_ME_MAGIC_ENERGIE
animationColor = GREEN
offensive = false
drawblood = false

BogRaiderHealObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
BogRaiderHealObject.minDmg = 65
BogRaiderHealObject.maxDmg = 95
return doTargetMagic(cid, centerpos, BogRaiderHealObject:ordered())
end
