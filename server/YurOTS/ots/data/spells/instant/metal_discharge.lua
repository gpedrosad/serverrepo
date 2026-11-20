area = {
{0, 0, 0, 0, 0, 0, 0},
{0, 0, 1, 1, 1, 0, 0},
{0, 1, 1, 1, 1, 1, 0},
{0, 1, 1, 0, 1, 1, 0},
{0, 1, 1, 1, 1, 1, 0},
{0, 0, 1, 1, 1, 0, 0},
{0, 0, 0, 0, 0, 0, 0},
}

-- Metal Hydra y Metal Demon: descarga eléctrica alrededor (anillo de 2 casillas).
attackType = ATTACK_ENERGY
needDirection = false
areaEffect = NM_ME_ENERGY_AREA
animationEffect = NM_ANI_NONE

hitEffect = NM_ME_ENERGY_DAMAGE
damageEffect = NM_ME_ENERGY_DAMAGE
animationColor = ENERGY
offensive = true
drawblood = false

DischargeObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
DischargeObject.minDmg = 90
DischargeObject.maxDmg = 180

return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, DischargeObject:ordered())
end
