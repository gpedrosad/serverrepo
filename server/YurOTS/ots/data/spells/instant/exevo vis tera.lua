-- Field Detonation (exevo vis tera), Sorcerer: detona hasta 3 campos mágicos
-- elementales (fuego/energía/veneno) en un área 3×3.

attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_NONE
damageEffect = NM_ME_DETONATION_RING
animationColor = ENERGY
offensive = true
drawblood = false

RADIUS = 1
MAX_FIELDS = 3
COOLDOWN_MS = 15000

PayObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	local remaining = spellCooldownReady(cid, "exevo vis tera")
	if remaining > 0 then
		return false
	end

	local centerpos = {x = creaturePos.x, y = creaturePos.y, z = creaturePos.z}
	local ret = doTargetMagic(cid, centerpos, PayObject:ordered())
	if ret then
		local baseMin = (level + maglv) * 1.5
		local baseMax = (level + maglv) * 2.5
		local detonated = doDetonateFields(cid, centerpos, RADIUS, MAX_FIELDS, baseMin, baseMax)
		if detonated > 0 then
			setSpellCooldown(cid, "exevo vis tera", COOLDOWN_MS)
		end
	end
	return ret
end
