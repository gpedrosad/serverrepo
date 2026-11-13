-- Generado por scripts/monsters/apply-monster-kits.py: burst, proyectil que estalla en 3x3, escalon 2 (8-28). No editar a mano.
area = {
{0,0,0,0,0},
{0,1,1,1,0},
{0,1,1,1,0},
{0,1,1,1,0},
{0,0,0,0,0}
}

needDirection = false
areaEffect = NM_ME_FIRE_AREA
attackType = ATTACK_FIRE
animationEffect = NM_ANI_BURSTARROW
hitEffect = NM_ME_FIRE_AREA
damageEffect = NM_ME_HITBY_FIRE
animationColor = FIRE
offensive = true
drawblood = false

KitObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
KitObject.minDmg = 8
KitObject.maxDmg = 28
return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, KitObject:ordered())
end
