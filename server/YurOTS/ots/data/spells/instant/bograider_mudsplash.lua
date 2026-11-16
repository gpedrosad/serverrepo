area = {
{0, 0, 0, 0, 0, 0, 0},
{0, 0, 1, 1, 1, 0, 0},
{0, 1, 1, 1, 1, 1, 0},
{0, 1, 1, 0, 1, 1, 0},
{0, 1, 1, 1, 1, 1, 0},
{0, 0, 1, 1, 1, 0, 0},
{0, 0, 0, 0, 0, 0, 0},
}

-- Bog Raider: salpicon de barro alrededor suyo (el golpe fisico en area del Bog Raider de 8.60).
-- Dano fisico con burbujas verdes de cienaga y numero verde.
attackType = ATTACK_PHYSICAL
needDirection = false
areaEffect = NM_ME_POISEN
animationEffect = NM_ANI_NONE

hitEffect = NM_ME_POISEN_RINGS
damageEffect = NM_ME_POISEN_RINGS
animationColor = GREEN
offensive = true
drawblood = false

BogRaiderMudsplashObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
BogRaiderMudsplashObject.minDmg = 40
BogRaiderMudsplashObject.maxDmg = 100

return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, BogRaiderMudsplashObject:ordered())
end
