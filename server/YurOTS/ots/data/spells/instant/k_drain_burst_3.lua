-- Generado por scripts/monsters/apply-monster-kits.py: drain, anillo alrededor suyo, escalon 3 (16-44). No editar a mano.
area = {
{0,0,0,0,0},
{0,1,1,1,0},
{0,1,0,1,0},
{0,1,1,1,0},
{0,0,0,0,0}
}

needDirection = false
areaEffect = NM_ME_MAGIC_BLOOD
attackType = ATTACK_LIFEDRAIN
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_MAGIC_BLOOD
damageEffect = NM_ME_MAGIC_BLOOD
animationColor = RED
offensive = true
drawblood = false

KitObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
KitObject.minDmg = 16
KitObject.maxDmg = 44
return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, KitObject:ordered())
end
