-- Blood Ritual (utamo mort), Sorcerer: convierte vida en maná durante unos segundos.
-- No funciona en PZ y nunca baja al jugador por debajo del 25 % de HP.

attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_NONE
damageEffect = NM_ME_BLOOD_SPIRAL
animationColor = PURPLE
offensive = false
drawblood = false

TOTAL_TICKS = 4
TICK_MS = 2000
HP_PER_TICK = 30
MANA_PER_TICK = 60
MIN_HP_PERCENT = 25
COOLDOWN_MS = 60000

PayObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	local remaining = spellCooldownReady(cid, "utamo mort")
	if remaining > 0 then
		return false
	end

	local centerpos = {x = creaturePos.x, y = creaturePos.y, z = creaturePos.z}
	local ret = doTargetMagic(cid, centerpos, PayObject:ordered())
	if ret then
		local ok = doBloodRitual(cid, TOTAL_TICKS, TICK_MS, HP_PER_TICK, MANA_PER_TICK, MIN_HP_PERCENT)
		if ok == 1 then
			setSpellCooldown(cid, "utamo mort", COOLDOWN_MS)
		end
	end
	return ret
end
