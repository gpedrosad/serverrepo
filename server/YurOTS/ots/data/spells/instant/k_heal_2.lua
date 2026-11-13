-- Generado por scripts/monsters/apply-monster-kits.py: cura propia, escalon 2. No editar a mano.
attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_NONE
damageEffect = NM_ME_MAGIC_ENERGIE
animationColor = GREEN
offensive = false
drawblood = false

KitHealObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
KitHealObject.minDmg = 10
KitHealObject.maxDmg = 35
return doTargetMagic(cid, centerpos, KitHealObject:ordered())
end
