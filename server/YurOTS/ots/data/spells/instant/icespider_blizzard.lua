area = {
{0, 0, 0, 0, 0, 0, 0},
{0, 0, 1, 1, 1, 0, 0},
{0, 1, 1, 1, 1, 1, 0},
{0, 1, 1, 0, 1, 1, 0},
{0, 1, 1, 1, 1, 1, 0},
{0, 0, 1, 1, 1, 0, 0},
{0, 0, 0, 0, 0, 0, 0},
}

-- Ice Spider: ventisca alrededor suyo (radio 2), version reducida del Frost Dragon.
-- 7.6 no tiene dano de hielo: dano fisico con los efectos del pack "ice" y numero celeste.
attackType = ATTACK_PHYSICAL
needDirection = false
areaEffect = NM_ME_ICE_HIT
animationEffect = NM_ANI_NONE

hitEffect = NM_ME_ICE_SHATTER
damageEffect = NM_ME_ICE_SHATTER
animationColor = LIGHT_BLUE
offensive = true
drawblood = false

IceSpiderBlizzardObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
IceSpiderBlizzardObject.minDmg = 45
IceSpiderBlizzardObject.maxDmg = 90

return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, IceSpiderBlizzardObject:ordered())
end
