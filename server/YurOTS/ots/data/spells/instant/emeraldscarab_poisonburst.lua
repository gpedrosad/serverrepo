area = {
{0, 0, 0, 0, 0, 0, 0},
{0, 0, 1, 1, 1, 0, 0},
{0, 1, 1, 1, 1, 1, 0},
{0, 1, 1, 0, 1, 1, 0},
{0, 1, 1, 1, 1, 1, 0},
{0, 0, 1, 1, 1, 0, 0},
{0, 0, 0, 0, 0, 0, 0},
}

-- Emerald Scarab: estallido de veneno inmediato alrededor suyo (radio 2).
attackType = ATTACK_POISON
needDirection = false
areaEffect = NM_ME_POISONCLOUD
animationEffect = NM_ANI_NONE

hitEffect = NM_ME_POISEN_RINGS
damageEffect = NM_ME_POISEN_RINGS
animationColor = GREEN
offensive = true
drawblood = false

EmeraldScarabPoisonObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
EmeraldScarabPoisonObject.minDmg = 45
EmeraldScarabPoisonObject.maxDmg = 85

return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, EmeraldScarabPoisonObject:ordered())
end
