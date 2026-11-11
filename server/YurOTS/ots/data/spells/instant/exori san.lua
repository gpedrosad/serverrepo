-- Divine Missile (exori san), Paladin: proyectil sagrado al blanco marcado, hasta 4 casillas.
--
-- Nov 2026, con la idea de las versiones nuevas y la fórmula de TFS 1.x:
--   mínimo = nivel / 5 + magic level * 1.79 + 11
--   máximo = nivel / 5 + magic level * 3 + 18
-- 7.6 no tiene daño sagrado: es daño de energía con proyectil de power bolt y anillos dorados.
-- Doc: docs/gameplay/SPELLS_NOV2026.md.

attackType = ATTACK_ENERGY
animationEffect = NM_ANI_POWERBOLT
hitEffect = NM_ME_YELLOW_RINGS
damageEffect = NM_ME_YELLOW_RINGS
animationColor = YELLOW
offensive = true
drawblood = false

RANGE = 4

MissileObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

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
	MissileObject.minDmg = level / 5 + maglv * 1.79 + 11
	MissileObject.maxDmg = level / 5 + maglv * 3 + 18
	return doTargetMagic(cid, target, MissileObject:ordered())
end
