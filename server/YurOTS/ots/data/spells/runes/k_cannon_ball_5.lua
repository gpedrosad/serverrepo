-- Generado por scripts/monsters/apply-monster-kits.py: cannon, proyectil que estalla en 3x3, escalon 5 (40-88). No editar a mano.
area = {
{0,0,0,0,0},
{0,1,1,1,0},
{0,1,1,1,0},
{0,1,1,1,0},
{0,0,0,0,0}
}

needDirection = false
areaEffect = NM_ME_EXPLOSION_AREA
attackType = ATTACK_PHYSICAL
animationEffect = NM_ANI_SMALLSTONE
hitEffect = NM_ME_EXPLOSION_DAMAGE
damageEffect = NM_ME_DRAW_BLOOD
animationColor = RED
offensive = true
drawblood = true

KitObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
KitObject.minDmg = 40
KitObject.maxDmg = 88
return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, KitObject:ordered())
end
