-- Dark Hydra: aliento de drenaje de vida, abanico direccional de la Hydra.
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

attackType = ATTACK_LIFEDRAIN
needDirection = true
areaEffect = NM_ME_MORT_AREA
animationEffect = NM_ANI_NONE

hitEffect = NM_ME_MORT_AREA
damageEffect = NM_ME_MORT_AREA
animationColor = PURPLE
offensive = true
drawblood = false

DarkHydraWaveObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
DarkHydraWaveObject.minDmg = 130
DarkHydraWaveObject.maxDmg = 220

return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, DarkHydraWaveObject:ordered())
end
