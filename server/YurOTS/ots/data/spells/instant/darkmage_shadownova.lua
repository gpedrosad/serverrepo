area = {
{0, 0, 0, 0, 0},
{0, 1, 1, 1, 0},
{0, 1, 0, 1, 0},
{0, 1, 1, 1, 0},
{0, 0, 0, 0, 0},
}

-- Dark Mage: anillo de sombra a su alrededor. Castiga a quien se le pega cuerpo a cuerpo.
attackType = ATTACK_LIFEDRAIN
needDirection = false
areaEffect = NM_ME_SHADOW_AREA
animationEffect = NM_ANI_NONE

hitEffect = NM_ME_SHADOW_IMPACT
damageEffect = NM_ME_SHADOW_IMPACT
animationColor = BLACK
offensive = true
drawblood = false

DarkMageNova = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
DarkMageNova.minDmg = 50
DarkMageNova.maxDmg = 90

return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, DarkMageNova:ordered())
end
