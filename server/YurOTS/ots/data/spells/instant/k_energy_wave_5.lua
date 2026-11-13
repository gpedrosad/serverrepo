-- Generado por scripts/monsters/apply-monster-kits.py: energy, onda en cono hacia adelante, escalon 5 (50-110). No editar a mano.
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
areaEffect = NM_ME_ENERGY_AREA
attackType = ATTACK_ENERGY
animationEffect = NM_ANI_NONE
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
return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, KitObject:ordered())
end
