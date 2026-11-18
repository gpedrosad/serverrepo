-- Counter Stance (utito tera), Knight: durante 5 s los próximos 2 golpes recibidos
-- hacen un 25 % menos de daño y devuelven el daño absorbido a monstruos.

attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_NONE
damageEffect = NM_ME_STANCE_GUARD
animationColor = YELLOW
offensive = false
drawblood = false

DURATION_S = 5
HITS = 2
REDUCTION = 25
COOLDOWN_MS = 30000

PayObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	local remaining = spellCooldownReady(cid, "utito tera")
	if remaining > 0 then
		return false
	end

	local centerpos = {x = creaturePos.x, y = creaturePos.y, z = creaturePos.z}
	local ret = doTargetMagic(cid, centerpos, PayObject:ordered())
	if ret then
		local ok = doCounterStance(cid, DURATION_S, HITS, REDUCTION)
		if ok == 1 then
			setSpellCooldown(cid, "utito tera", COOLDOWN_MS)
		end
	end
	return ret
end
