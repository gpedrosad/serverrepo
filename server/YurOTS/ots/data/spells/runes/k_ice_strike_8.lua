-- Generado por scripts/monsters/apply-monster-kits.py: ice, proyectil al blanco, escalon 8 (140-270). No editar a mano.
attackType = ATTACK_PHYSICAL
animationEffect = NM_ANI_FROSTBALL
hitEffect = NM_ME_ICE_HIT
damageEffect = NM_ME_ICE_SHATTER
animationColor = LIGHT_BLUE
offensive = true
drawblood = false

KitObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
KitObject.minDmg = 140
KitObject.maxDmg = 270
return doTargetMagic(cid, centerpos, KitObject:ordered())
end
