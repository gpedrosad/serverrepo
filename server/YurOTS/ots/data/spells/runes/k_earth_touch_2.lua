-- Generado por scripts/monsters/apply-monster-kits.py: earth, golpe sin proyectil (mordida, picadura), escalon 2 (10-35). No editar a mano.
attackType = ATTACK_PHYSICAL
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_HIT_AREA
damageEffect = NM_ME_DRAW_BLOOD
animationColor = RED
offensive = true
drawblood = true

KitObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
KitObject.minDmg = 10
KitObject.maxDmg = 35
return doTargetMagic(cid, centerpos, KitObject:ordered())
end
