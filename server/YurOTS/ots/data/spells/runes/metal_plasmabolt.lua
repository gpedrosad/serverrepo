area = {
{0, 0, 0, 0, 0},
{0, 1, 1, 1, 0},
{0, 1, 1, 1, 0},
{0, 1, 1, 1, 0},
{0, 0, 0, 0, 0},
}

-- Metal Dragon y Metal Demon: bola de plasma que estalla en 3x3 sobre el objetivo.
attackType = ATTACK_ENERGY
needDirection = false
areaEffect = NM_ME_ENERGY_AREA
animationEffect = NM_ANI_ENERGY

hitEffect = NM_ME_ENERGY_DAMAGE
damageEffect = NM_ME_ENERGY_DAMAGE
animationColor = ENERGY
offensive = true
drawblood = false

PlasmaBoltObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
PlasmaBoltObject.minDmg = 80
PlasmaBoltObject.maxDmg = 150

return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, PlasmaBoltObject:ordered())
end
