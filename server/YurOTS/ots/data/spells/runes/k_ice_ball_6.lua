-- Generado por scripts/monsters/apply-monster-kits.py: ice, proyectil que estalla en 3x3, escalon 6 (56-120). No editar a mano.
area = {
{0,0,0,0,0},
{0,1,1,1,0},
{0,1,1,1,0},
{0,1,1,1,0},
{0,0,0,0,0}
}

needDirection = false
areaEffect = NM_ME_ICE_AREA
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
KitObject.minDmg = 56
KitObject.maxDmg = 120
return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, KitObject:ordered())
end
