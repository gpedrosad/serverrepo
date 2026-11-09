area = {
{0, 0, 0, 0, 0, 0, 0},
{0, 0, 1, 1, 1, 0, 0},
{0, 1, 1, 1, 1, 1, 0},
{0, 1, 1, 0, 1, 1, 0},
{0, 1, 1, 1, 1, 1, 0},
{0, 0, 1, 1, 1, 0, 0},
{0, 0, 0, 0, 0, 0, 0},
}

-- Frost Dragon: ventisca alrededor suyo (radio 2). Castiga quedarse pegado.
attackType = ATTACK_PHYSICAL
needDirection = false
areaEffect = NM_ME_ICE_HIT
animationEffect = NM_ANI_NONE

hitEffect = NM_ME_ICE_SHATTER
damageEffect = NM_ME_ICE_SHATTER
animationColor = LIGHT_BLUE
offensive = true
drawblood = false

BlizzardObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
BlizzardObject.minDmg = 100
BlizzardObject.maxDmg = 180

return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, BlizzardObject:ordered())
end
