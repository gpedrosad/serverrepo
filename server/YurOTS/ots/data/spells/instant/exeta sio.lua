-- Rescue (exeta sio), Knight: los monstruos que atacan a un aliado pasan a atacar al Knight.
-- Solo PvE. El aliado se indica con su nombre ("exeta sio Nombre").

attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_NONE
damageEffect = NM_ME_RALLY_RING
animationColor = LIGHT_BLUE
offensive = true
drawblood = false

RADIUS = 4
DURATION_S = 4
COOLDOWN_MS = 20000

PayObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	local remaining = spellCooldownReady(cid, "exeta sio")
	if remaining > 0 then
		return false
	end

	if var == nil or var == "" then
		return false
	end

	local centerpos = {x = creaturePos.x, y = creaturePos.y, z = creaturePos.z}
	local ret = doTargetMagic(cid, centerpos, PayObject:ordered())
	if ret then
		local affected = doRescue(cid, var, RADIUS, DURATION_S)
		if affected > 0 then
			setSpellCooldown(cid, "exeta sio", COOLDOWN_MS)
		end
	end
	return ret
end
