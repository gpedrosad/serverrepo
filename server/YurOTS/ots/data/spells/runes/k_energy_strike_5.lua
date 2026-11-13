-- Generado por scripts/monsters/apply-monster-kits.py: energy, proyectil al blanco, escalon 5 (50-110). No editar a mano.
attackType = ATTACK_ENERGY
animationEffect = NM_ANI_ENERGY
hitEffect = NM_ME_ENERGY_AREA
damageEffect = NM_ME_ENERGY_DAMAGE
animationColor = ENERGY
offensive = true
drawblood = false

KitObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
KitObject.minDmg = 50
KitObject.maxDmg = 110
return doTargetMagic(cid, centerpos, KitObject:ordered())
end
