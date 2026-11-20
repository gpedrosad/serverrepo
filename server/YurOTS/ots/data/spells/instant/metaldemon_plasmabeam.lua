area = {
{0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0},
{2, 2, 2, 2, 2, 2, 0, 3, 3, 3, 3, 3, 3},
{0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0},
{0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0}
}

-- Metal Demon: rayo de plasma rojo en línea (misma forma que el rayo del Demon).
attackType = ATTACK_FIRE
needDirection = true
areaEffect = NM_ME_EXPLOSION_AREA
animationEffect = NM_ANI_NONE

hitEffect = NM_ME_EXPLOSION_DAMAGE
damageEffect = NM_ME_HITBY_FIRE
animationColor = RED
offensive = true
drawblood = false

PlasmaBeamObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
PlasmaBeamObject.minDmg = 320
PlasmaBeamObject.maxDmg = 460

return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, PlasmaBeamObject:ordered())
end
