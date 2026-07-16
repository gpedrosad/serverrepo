-- Energy Strike Hur: ranged energy hit on battle-list target (like exori hur).
-- Damage formula = exori vis. Visuals = Heavy Magic Missile. Sorc/Druid.

attackType = ATTACK_ENERGY
animationEffect = NM_ANI_FIRE

hitEffect = NM_ME_EXPLOSION_DAMAGE
damageEffect = NM_ME_ENERGY_DAMAGE
animationColor = LIGHT_BLUE
offensive = true
drawblood = true

RANGE = 5

ExoriVisHurObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	ExoriVisHurObject.minDmg = (level * 1 + maglv * 1) * 0.8
	ExoriVisHurObject.maxDmg = (level * 1 + maglv * 1)

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

	if dx == 0 and dy == 0 then
		return false
	end

	local success = doTargetMagic(cid, targetpos, ExoriVisHurObject:ordered())
	if success then
		reduceExhaustion(cid)
	end
	return success
end
