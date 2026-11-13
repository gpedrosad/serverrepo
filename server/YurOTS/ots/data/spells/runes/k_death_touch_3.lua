-- Generado por scripts/monsters/apply-monster-kits.py: death, golpe sin proyectil (mordida, picadura), escalon 3 (20-55). No editar a mano.
attackType = ATTACK_PHYSICAL
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_MORT_AREA
damageEffect = NM_ME_MORT_AREA
animationColor = GREY
offensive = true
drawblood = false

KitObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
KitObject.minDmg = 20
KitObject.maxDmg = 55
return doTargetMagic(cid, centerpos, KitObject:ordered())
end
