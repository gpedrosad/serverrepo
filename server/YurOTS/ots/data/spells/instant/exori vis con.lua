-- Chain Lightning (exori vis con), Sorcerer: salta entre monstruos cercanos.
-- El blanco inicial debe ser un monstruo. Los rebotes solo buscan monstruos.

attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_NONE
damageEffect = NM_ME_ENERGY_DAMAGE
animationColor = ENERGY
offensive = true
drawblood = false

JUMPS = 2
RANGE = 3
FALLOFF = 55 -- % del daño en cada salto
COOLDOWN_MS = 10000

PayObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	local remaining = spellCooldownReady(cid, "exori vis con")
	if remaining > 0 then
		return false
	end

	local target = getAttackedCreaturePos(cid)
	if target.x == nil or target.z ~= creaturePos.z then
		return false
	end

	local centerpos = {x = creaturePos.x, y = creaturePos.y, z = creaturePos.z}
	local ret = doTargetMagic(cid, centerpos, PayObject:ordered())
	if ret then
		local baseMin = (level + maglv) * 1.2
		local baseMax = (level + maglv) * 1.8
		local affected = doChainLightning(cid, target, JUMPS, RANGE, FALLOFF, baseMin, baseMax)
		if affected > 0 then
			setSpellCooldown(cid, "exori vis con", COOLDOWN_MS)
		end
	end
	return ret
end
