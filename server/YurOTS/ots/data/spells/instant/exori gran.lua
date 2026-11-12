-- 12 casillas: el anillo 3x3 del exori (8) más una en cada dirección. Antes era un diamante de 24.
area = {
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0},
    {0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0},
    {0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    }

    attackType = ATTACK_PHYSICAL
    needDirection = false
    areaEffect = NM_ME_WHIRL_SLASH    -- tajo que gira (pack "gran", efecto 35)
    animationEffect = NM_ANI_NONE

    hitEffect = NM_ME_DRAW_BLOOD
    damageEffect = NM_ME_DRAW_BLOOD
    animationColor = RED
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
        BerserkGranObject.minDmg = (level * 1.5 + maglv * 1.5) * 1.32
        BerserkGranObject.maxDmg = (level * 1.5 + maglv * 1.5) * 2.53
    end

    return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, BerserkGranObject:ordered())
    end
