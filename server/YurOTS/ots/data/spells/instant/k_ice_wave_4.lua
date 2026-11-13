-- Generado por scripts/monsters/apply-monster-kits.py: ice, onda en cono hacia adelante, escalon 4 (35-80). No editar a mano.
area = {
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0},
{0,0,0,0,2,2,0,0,1,0,0,3,3,0,0,0,0},
{0,0,0,0,2,2,2,2,0,3,3,3,3,0,0,0,0},
{0,0,0,0,2,2,0,0,4,0,0,3,3,0,0,0,0},
{0,0,0,0,0,0,0,0,4,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,4,4,4,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,4,4,4,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}
}

needDirection = true
areaEffect = NM_ME_ICE_AREA
attackType = ATTACK_PHYSICAL
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_ICE_HIT
damageEffect = NM_ME_ICE_SHATTER
animationColor = LIGHT_BLUE
offensive = true
drawblood = false

KitObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
KitObject.minDmg = 35
KitObject.maxDmg = 80
return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, KitObject:ordered())
end
