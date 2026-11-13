-- Generado por scripts/monsters/apply-monster-kits.py: drain, proyectil al blanco, escalon 2 (10-35). No editar a mano.
attackType = ATTACK_LIFEDRAIN
animationEffect = NM_ANI_SHADOWBALL
hitEffect = NM_ME_MAGIC_BLOOD
damageEffect = NM_ME_MAGIC_BLOOD
animationColor = RED
offensive = true
drawblood = false

KitObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
KitObject.minDmg = 10
KitObject.maxDmg = 35
return doTargetMagic(cid, centerpos, KitObject:ordered())
end
