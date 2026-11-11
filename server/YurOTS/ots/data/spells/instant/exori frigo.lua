-- Ice Strike (exori frigo), Druid: golpe de hielo al blanco marcado, hasta 3 casillas.
--
-- Nov 2026, con la idea de las versiones nuevas. Mismo daño que exori flam / exori vis del servidor:
-- (nivel + magic level) * 0.8 a * 1.0, y la misma espera corta (reduceExhaustion).
-- 7.6 no tiene daño de hielo: es físico con la bola y los efectos de hielo del pack "ice" (como los
-- monstruos de hielo). Con un cliente viejo el daño llega pero no se ven. Doc: docs/gameplay/SPELLS_NOV2026.md.

attackType = ATTACK_PHYSICAL
animationEffect = NM_ANI_FROSTBALL
hitEffect = NM_ME_ICE_SHATTER
damageEffect = NM_ME_ICE_HIT
animationColor = LIGHT_BLUE
offensive = true
drawblood = false

RANGE = 3

IceObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	local target = getAttackedCreaturePos(cid)
	if target.x == nil or target.z ~= creaturePos.z then
		return false
	end
	local dx = math.abs(target.x - creaturePos.x)
	local dy = math.abs(target.y - creaturePos.y)
	if (dx == 0 and dy == 0) or dx > RANGE or dy > RANGE then
		return false
	end
	IceObject.minDmg = (level + maglv) * 0.8
	IceObject.maxDmg = (level + maglv) * 1.0
	local success = doTargetMagic(cid, target, IceObject:ordered())
	if success then
		reduceExhaustion(cid)
	end
	return success
end
