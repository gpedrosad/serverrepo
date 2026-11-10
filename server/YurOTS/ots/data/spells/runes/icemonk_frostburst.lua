area = {
{0, 0, 0, 0, 0},
{0, 0, 1, 0, 0},
{0, 1, 1, 1, 0},
{0, 0, 1, 0, 0},
{0, 0, 0, 0, 0},
}

-- Ice Monk: bola de hielo que estalla en cruz sobre el objetivo (más débil que la del Frost Dragon).
attackType = ATTACK_PHYSICAL
needDirection = false
areaEffect = NM_ME_ICE_EXPLOSION
animationEffect = NM_ANI_FROSTBALL

hitEffect = NM_ME_ICE_SHATTER
damageEffect = NM_ME_ICE_SHATTER
animationColor = LIGHT_BLUE
offensive = true
drawblood = false

FrostBurstObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
FrostBurstObject.minDmg = 30
FrostBurstObject.maxDmg = 70

return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, FrostBurstObject:ordered())
end
