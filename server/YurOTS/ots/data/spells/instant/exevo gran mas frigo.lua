-- Eternal Winter (exevo gran mas frigo), Druid: tormenta de hielo alrededor (mismo rombo que Poison Storm).
--
-- Nov 2026, con la idea de las versiones nuevas (la versión de druid del Hell's Core). Daño de un golpe,
-- sin veneno que siga: (nivel * 2 + magic level * 3) * 1.3 a * 2.0.
-- 7.6 no tiene daño de hielo: es físico con los efectos del pack "ice". Doc: docs/gameplay/SPELLS_NOV2026.md.

area = {
	{0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0},
	{0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0},
	{0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0},
	{0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0},
	{0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0},
	{1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1},
	{0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0},
	{0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0},
	{0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0},
	{0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0},
	{0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0},
}

attackType = ATTACK_PHYSICAL
needDirection = false
areaEffect = NM_ME_ICE_AREA
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_ICE_SHATTER
damageEffect = NM_ME_ICE_HIT
animationColor = LIGHT_BLUE
offensive = true
drawblood = false

WinterObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	local centerpos = {x = creaturePos.x, y = creaturePos.y, z = creaturePos.z}
	WinterObject.minDmg = (level * 2 + maglv * 3) * 1.3
	WinterObject.maxDmg = (level * 2 + maglv * 3) * 2.0
	return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, WinterObject:ordered())
end
