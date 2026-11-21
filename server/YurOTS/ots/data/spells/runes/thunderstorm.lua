-- Thunderstorm Rune (2315) — 7x7 energy area rune.
area = {
	{0, 0, 1, 1, 1, 0, 0},
	{0, 1, 1, 1, 1, 1, 0},
	{1, 1, 1, 1, 1, 1, 1},
	{1, 1, 1, 1, 1, 1, 1},
	{1, 1, 1, 1, 1, 1, 1},
	{0, 1, 1, 1, 1, 1, 0},
	{0, 0, 1, 1, 1, 0, 0}
}

attackType = ATTACK_ENERGY
needDirection = false
areaEffect = NM_ME_ENERGY_AREA
animationEffect = NM_ANI_ENERGY

hitEffect = NM_ME_ENERGY_DAMAGE
damageEffect = NM_ME_ENERGY_DAMAGE
animationColor = LIGHT_BLUE
offensive = true
drawblood = false

ThunderstormObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}

	ThunderstormObject.minDmg = (level * 2 + maglv * 3) * 0.38
	ThunderstormObject.maxDmg = (level * 2 + maglv * 3) * 0.72

	return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, ThunderstormObject:ordered())
end
