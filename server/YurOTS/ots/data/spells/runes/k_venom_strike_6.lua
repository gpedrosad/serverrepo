-- Generado por scripts/monsters/apply-monster-kits.py: venom, proyectil al blanco, escalon 6 (70-150). No editar a mano.
attackType = ATTACK_POISON
animationEffect = NM_ANI_POISONARROW
hitEffect = NM_ME_POISEN_RINGS
damageEffect = NM_ME_POISEN_RINGS
animationColor = GREEN
offensive = true
drawblood = true

KitObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
KitObject.minDmg = 70
KitObject.maxDmg = 150
return doTargetMagic(cid, centerpos, KitObject:ordered())
end
