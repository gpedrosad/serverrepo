-- Stone Shower Rune (2288) — 7x7 physical/earth area rune.
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
areaEffect = NM_ME_EXPLOSION_AREA
animationEffect = NM_ANI_SMALLSTONE

hitEffect = NM_ME_HIT_AREA
damageEffect = NM_ME_DRAW_BLOOD
animationColor = GREY
offensive = true
drawblood = true

StoneShowerObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}

	StoneShowerObject.minDmg = (level * 2 + maglv * 3) * 0.38
	StoneShowerObject.maxDmg = (level * 2 + maglv * 3) * 0.72

	return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, StoneShowerObject:ordered())
end
