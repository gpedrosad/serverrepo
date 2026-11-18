-- Seed of Life (exura tera), Druid: cura inmediata y una cura mayor 3 s después
-- si el aliado sigue cerca. El aliado se indica con su nombre.

attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_NONE
damageEffect = NM_ME_SEED_BURST
animationColor = GREEN
offensive = false
drawblood = false

DELAY_MS = 3000
RANGE = 6
COOLDOWN_MS = 20000

PayObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	local remaining = spellCooldownReady(cid, "exura tera")
	if remaining > 0 then
		return false
	end

	if var == nil or var == "" then
		return false
	end

	local centerpos = {x = creaturePos.x, y = creaturePos.y, z = creaturePos.z}
	local ret = doTargetMagic(cid, centerpos, PayObject:ordered())
	if ret then
		local immediateMin = (level * 2 + maglv * 3) * 0.15
		local immediateMax = (level * 2 + maglv * 3) * 0.30
		local delayedMin = (level * 2 + maglv * 3) * 0.35
		local delayedMax = (level * 2 + maglv * 3) * 0.55
		local ok = doDelayedHeal(cid, var, immediateMin, immediateMax, DELAY_MS, delayedMin, delayedMax, RANGE)
		if ok == 1 then
			setSpellCooldown(cid, "exura tera", COOLDOWN_MS)
		end
	end
	return ret
end
