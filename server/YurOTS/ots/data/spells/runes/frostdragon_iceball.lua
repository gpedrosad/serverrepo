area = {
{0, 0, 0, 0, 0},
{0, 0, 1, 0, 0},
{0, 1, 1, 1, 0},
{0, 0, 1, 0, 0},
{0, 0, 0, 0, 0},
}

-- Frost Dragon: bola de hielo a distancia (proyectil nuevo) que estalla en cruz sobre el objetivo.
attackType = ATTACK_PHYSICAL
needDirection = false
areaEffect = NM_ME_ICE_EXPLOSION
animationEffect = NM_ANI_FROSTBALL

hitEffect = NM_ME_ICE_SHATTER
damageEffect = NM_ME_ICE_SHATTER
animationColor = LIGHT_BLUE
offensive = true
drawblood = false

IceballObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
IceballObject.minDmg = 80
IceballObject.maxDmg = 150

return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, IceballObject:ordered())
end
