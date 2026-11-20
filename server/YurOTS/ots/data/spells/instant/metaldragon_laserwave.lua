area = {
{0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0},
{2, 2, 2, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 3, 3, 3},
{2, 2, 2, 2, 2, 0, 0, 0, 1, 0, 0, 0, 3, 3, 3, 3, 3},
{2, 2, 2, 2, 2, 2, 0, 0, 1, 0, 0, 3, 3, 3, 3, 3, 3},
{2, 2, 2, 2, 2, 2, 2, 2, 0, 3, 3, 3, 3, 3, 3, 3, 3},
{2, 2, 2, 2, 2, 2, 0, 0, 4, 0, 0, 3, 3, 3, 3, 3, 3},
{2, 2, 2, 2, 2, 0, 0, 0, 4, 0, 0, 0, 3, 3, 3, 3, 3},
{2, 2, 2, 0, 0, 0, 0, 4, 4, 4, 0, 0, 0, 0, 3, 3, 3},
{0, 0, 0, 0, 0, 0, 4, 4, 4, 4, 4, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 4, 4, 4, 4, 4, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 4, 4, 4, 4, 4, 4, 4, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 4, 4, 4, 4, 4, 4, 4, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 4, 4, 4, 4, 4, 4, 4, 0, 0, 0, 0, 0}
}

-- Metal Dragon: láser de energía en abanico (misma forma que el aliento del Dragon Lord).
attackType = ATTACK_ENERGY
needDirection = true
areaEffect = NM_ME_ENERGY_AREA
animationEffect = NM_ANI_NONE

hitEffect = NM_ME_ENERGY_DAMAGE
damageEffect = NM_ME_ENERGY_DAMAGE
animationColor = ENERGY
offensive = true
drawblood = false

LaserWaveObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
LaserWaveObject.minDmg = 180
LaserWaveObject.maxDmg = 300

return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, LaserWaveObject:ordered())
end
