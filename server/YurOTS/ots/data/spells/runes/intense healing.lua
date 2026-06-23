attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE

hitEffect = NM_ME_NONE
damageEffect = NM_ME_MAGIC_ENERGIE
animationColor = GREEN
offensive = false
drawblood = false

IntenseHealingObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}

IntenseHealingObject.minDmg = (level * 2 + maglv * 3) * 1.4
if IntenseHealingObject.minDmg < 100 then
	IntenseHealingObject.minDmg = 100
end

IntenseHealingObject.maxDmg = (level * 2 + maglv * 3) * 2.0
if IntenseHealingObject.maxDmg < 100 then
	IntenseHealingObject.maxDmg = 100
end

return doTargetMagic(cid, centerpos, IntenseHealingObject:ordered())
end
