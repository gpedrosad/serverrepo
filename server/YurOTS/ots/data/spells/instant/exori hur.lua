-- Whirlwind Throw: ranged physical hit on the caster's current attack target.
-- Range 5 (Chebyshev). Projectile: large rock. Requires line of sight (doTargetMagic).

attackType = ATTACK_PHYSICAL
animationEffect = NM_ANI_LARGEROCK

hitEffect = NM_ME_DRAW_BLOOD
damageEffect = NM_ME_HIT_AREA
animationColor = RED
offensive = true
drawblood = true

RANGE = 5

ExoriHurObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	ExoriHurObject.minDmg = (level * 1 + maglv * 1) * 1.0
	ExoriHurObject.maxDmg = (level * 1 + maglv * 1) * 1.8

	local targetpos = getAttackedCreaturePos(cid)
	if targetpos.x == nil or targetpos.y == nil or targetpos.z == nil then
		return false
	end

	if targetpos.z ~= creaturePos.z then
		return false
	end

	local dx = math.abs(targetpos.x - creaturePos.x)
	local dy = math.abs(targetpos.y - creaturePos.y)
	if dx > RANGE or dy > RANGE then
		return false
	end

	-- Need a real target tile (not self).
	if dx == 0 and dy == 0 then
		return false
	end

	return doTargetMagic(cid, targetpos, ExoriHurObject:ordered())
end
