-- Generado por scripts/monsters/apply-monster-kits.py: roar, anillo alrededor suyo, escalon 2 (8-28). No editar a mano.
area = {
{0,0,0,0,0},
{0,1,1,1,0},
{0,1,0,1,0},
{0,1,1,1,0},
{0,0,0,0,0}
}

needDirection = false
areaEffect = NM_ME_SOUND_RED
attackType = ATTACK_PHYSICAL
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_SOUND_RED
damageEffect = NM_ME_DRAW_BLOOD
animationColor = RED
offensive = true
drawblood = true

KitObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
KitObject.minDmg = 8
KitObject.maxDmg = 28
return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, KitObject:ordered())
end
