-- Cleanse (exana res), Druid: quita poison y paralyze de un jugador aliado.
-- No cura root (Anchor). El aliado se indica con su nombre.

attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_NONE
damageEffect = NM_ME_MAGIC_ENERGIE
animationColor = GREEN
offensive = false
drawblood = false

COOLDOWN_MS = 25000

PayObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	local remaining = spellCooldownReady(cid, "exana res")
	if remaining > 0 then
		return false
	end

	if var == nil or var == "" then
		return false
	end

	local centerpos = {x = creaturePos.x, y = creaturePos.y, z = creaturePos.z}
	local ret = doTargetMagic(cid, centerpos, PayObject:ordered())
	if ret then
		local ok = doCleanse(cid, var)
		if ok == 1 then
			setSpellCooldown(cid, "exana res", COOLDOWN_MS)
		end
	end
	return ret
end
