area = {
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0},
    {0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0},
    {0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0},
    {0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0},
    {0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    }

    attackType = ATTACK_PHYSICAL
    needDirection = false
    areaEffect = NM_ME_EXPLOSION_AREA
    animationEffect = NM_ANI_NONE

    hitEffect = NM_ME_DRAW_BLOOD
    damageEffect = NM_ME_EXPLOSION_AREA
    animationColor = ORANGE
    offensive = true
    drawblood = true

    BerserkGranObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

    function onCast(cid, creaturePos, level, maglv, var)
    centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
    n = tonumber(var)
    if n ~= nil then
        BerserkGranObject.minDmg = 0
        BerserkGranObject.maxDmg = 0
    else
        BerserkGranObject.minDmg = (level * 2 + maglv * 3) * 2.8 - 30
        BerserkGranObject.maxDmg = (level * 2 + maglv * 3) * 3.6
    end

    return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, BerserkGranObject:ordered())
    end
