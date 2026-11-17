-- Piercing Volley (exori con gran), Paladin: ráfaga física en línea recta.
-- Daño escala con nivel + skill de distancia. 5 casillas de alcance.

attackType = ATTACK_PHYSICAL
needDirection = false
areaEffect = NM_ME_HIT_AREA
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_DRAW_BLOOD
damageEffect = NM_ME_HIT_AREA
animationColor = RED
offensive = true
drawblood = true

RANGE = 5
COOLDOWN_MS = 8000
SKILL_DIST = 4

LINE = {
	n = {{0, -1}, {0, -2}, {0, -3}, {0, -4}, {0, -5}},
	s = {{0, 1}, {0, 2}, {0, 3}, {0, 4}, {0, 5}},
	e = {{1, 0}, {2, 0}, {3, 0}, {4, 0}, {5, 0}},
	w = {{-1, 0}, {-2, 0}, {-3, 0}, {-4, 0}, {-5, 0}},
}

local function lineArea(dir)
	local area = {}
	for y = -5, 5 do
		area[y + 6] = {}
		for x = -5, 5 do
			area[y + 6][x + 6] = 0
		end
	end
	for i = 1, table.getn(LINE[dir]) do
		local d = LINE[dir][i]
		area[d[2] + 6][d[1] + 6] = 1
	end
	return area
end

VolleyObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	local remaining = spellCooldownReady(cid, "exori con gran")
	if remaining > 0 then
		return false
	end

	local distance = getPlayerSkill(cid, SKILL_DIST)
	if distance < 0 then
		return false
	end

	local dir = getCreatureDirection(cid)
	if LINE[dir] == nil then
		return false
	end

	VolleyObject.minDmg = level / 5 + distance * 0.6
	VolleyObject.maxDmg = level / 5 + distance * 1.2 + 10

	local centerpos = {x = creaturePos.x, y = creaturePos.y, z = creaturePos.z}
	local ret = doAreaMagic(cid, centerpos, needDirection, areaEffect, lineArea(dir), VolleyObject:ordered())
	if ret then
		setSpellCooldown(cid, "exori con gran", COOLDOWN_MS)
	end
	return ret
end
