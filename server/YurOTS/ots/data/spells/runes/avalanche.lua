-- Avalanche Rune (2274) — 7x7 ice area rune (adapted to 7.6 with pack "ice" effects).
area = {
	{0, 0, 1, 1, 1, 0, 0},
	{0, 1, 1, 1, 1, 1, 0},
	{1, 1, 1, 1, 1, 1, 1},
	{1, 1, 1, 1, 1, 1, 1},
	{1, 1, 1, 1, 1, 1, 1},
	{0, 1, 1, 1, 1, 1, 0},
	{0, 0, 1, 1, 1, 0, 0}
}

attackType = ATTACK_PHYSICAL
needDirection = false
areaEffect = NM_ME_ICE_AREA
animationEffect = NM_ANI_FROSTBALL

hitEffect = NM_ME_ICE_SHATTER
damageEffect = NM_ME_ICE_HIT
animationColor = LIGHT_BLUE
offensive = true
drawblood = false

AvalancheObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}

	AvalancheObject.minDmg = (level * 2 + maglv * 3) * 0.40
	AvalancheObject.maxDmg = (level * 2 + maglv * 3) * 0.75

	return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, AvalancheObject:ordered())
end
