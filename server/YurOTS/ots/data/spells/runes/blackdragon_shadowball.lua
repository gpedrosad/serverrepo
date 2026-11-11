area = {
{0, 0, 0, 0, 0},
{0, 1, 1, 1, 0},
{0, 1, 1, 1, 0},
{0, 1, 1, 1, 0},
{0, 0, 0, 0, 0},
}

-- Black Dragon: bola de sombra que estalla en 3x3 sobre el objetivo y drena vida (pack "shadow").
-- Reemplaza la firebomb que usaba antes: no deja campos de fuego.
attackType = ATTACK_LIFEDRAIN
needDirection = false
areaEffect = NM_ME_SHADOW_EXPLOSION
animationEffect = NM_ANI_SHADOWBALL

hitEffect = NM_ME_SHADOW_IMPACT
damageEffect = NM_ME_SHADOW_IMPACT
animationColor = BLACK
offensive = true
drawblood = false

ShadowBallObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
ShadowBallObject.minDmg = 60
ShadowBallObject.maxDmg = 120

return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, ShadowBallObject:ordered())
end
