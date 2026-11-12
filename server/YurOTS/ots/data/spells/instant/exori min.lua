-- Front Sweep (exori min), Knight: barrido con el arma a las 3 casillas de adelante (la del frente y sus
-- dos costados), hacia donde mira.
--
-- Nov 2026, con la idea de las versiones nuevas (8.x en adelante) y la fórmula de TFS 1.x:
--   mínimo = nivel / 5 + (skill + ataque del arma) * 0.5
--   máximo = nivel / 5 + (skill + ataque del arma) * 1.1
-- Necesita espada, hacha o maza en la mano. El área se arma en Lua según la dirección (getCreatureDirection):
-- con needDirection el área no puede repetir las esquinas entre dos direcciones.
-- Doc: docs/gameplay/SPELLS_NOV2026.md.

attackType = ATTACK_PHYSICAL
needDirection = false
areaEffect = NM_ME_HIT_AREA
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_DRAW_BLOOD
damageEffect = NM_ME_HIT_AREA
animationColor = RED
offensive = true
drawblood = true

SKILLS = {club = 1, sword = 2, axe = 3}
-- casillas (dx, dy) del barrido según hacia dónde mira el knight
FRONT = {
	n = {{-1, -1}, {0, -1}, {1, -1}},
	s = {{-1, 1}, {0, 1}, {1, 1}},
	w = {{-1, -1}, {-1, 0}, {-1, 1}},
	e = {{1, -1}, {1, 0}, {1, 1}},
}

SweepObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

-- Área 3x3 centrada en el knight con 1 en las casillas del barrido (sin dirección, el servidor usa las de valor 1).
local function sweepArea(dir)
	local area = {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}}
	for i = 1, table.getn(FRONT[dir]) do
		local d = FRONT[dir][i]
		area[d[2] + 2][d[1] + 2] = 1
	end
	return area
end

function onCast(cid, creaturePos, level, maglv, var)
	local weapon = getPlayerWeapon(cid)
	local skillId = SKILLS[weapon.type]
	local dir = getCreatureDirection(cid)
	if skillId == nil or FRONT[dir] == nil then
		return false
	end
	local skill = getPlayerSkill(cid, skillId)
	if skill < 0 then
		return false
	end
	SweepObject.minDmg = level / 5 + (skill + weapon.attack) * 0.5
	SweepObject.maxDmg = level / 5 + (skill + weapon.attack) * 1.1
	local centerpos = {x = creaturePos.x, y = creaturePos.y, z = creaturePos.z}
	return doAreaMagic(cid, centerpos, needDirection, areaEffect, sweepArea(dir), SweepObject:ordered())
end
