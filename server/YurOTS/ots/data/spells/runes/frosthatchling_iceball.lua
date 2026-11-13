-- Frost Dragon Hatchling: bola de hielo.
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

FrostHatchlingIceballObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
FrostHatchlingIceballObject.minDmg = 40
FrostHatchlingIceballObject.maxDmg = 80

return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, FrostHatchlingIceballObject:ordered())
end
