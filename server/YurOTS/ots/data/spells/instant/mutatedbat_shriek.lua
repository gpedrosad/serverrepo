-- Mutated Bat: chillido en cono (5 casillas).
area = {
{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 2, 2, 2, 2, 0, 1, 0, 3, 3, 3, 3, 0, 0, 0},
{0, 0, 0, 2, 2, 2, 2, 2, 0, 3, 3, 3, 3, 3, 0, 0, 0},
{0, 0, 0, 2, 2, 2, 2, 0, 4, 0, 3, 3, 3, 3, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 0, 4, 4, 4, 0, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 0, 4, 4, 4, 0, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 0, 4, 4, 4, 0, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 0, 4, 4, 4, 0, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}
}

attackType = ATTACK_PHYSICAL
needDirection = true
areaEffect = NM_ME_SOUND_PURPLE
animationEffect = NM_ANI_NONE

hitEffect = NM_ME_SOUND_PURPLE
damageEffect = NM_ME_DRAW_BLOOD
animationColor = RED
offensive = true
drawblood = false

MutatedBatShriekObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
MutatedBatShriekObject.minDmg = 70
MutatedBatShriekObject.maxDmg = 160

return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, MutatedBatShriekObject:ordered())
end
