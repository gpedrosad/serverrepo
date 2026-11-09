-- Base: reloj, distancia al jugador, movimiento y coincidencia de palabras.
-- Parte de lib/npc.lua (ver docs/gameplay/NPC_SYSTEM.md).

-- Segundos reales. No usar os.clock(): es tiempo de CPU del proceso, que en un servidor
-- casi ocioso avanza mucho más lento que el reloj (un timeout de 30 s duraba minutos).
function npcNow()
	return os.time()
end

function getDistanceToCreature(id)
	if id == 0 or id == nil then
		selfGotoIdle()
		return nil
	end
	local cx, cy, cz = creatureGetPosition(id)
	if cx == nil then
		return nil
	end
	local sx, sy, sz = selfGetPosition()
	return math.max(math.abs(sx - cx), math.abs(sy - cy))
end

-- true si `str` aparece en `txt` como palabra(s) completa(s). Busca texto literal: las claves
-- con '-', '.', '(' etc. funcionan ("two-handed sword"); antes se interpretaban como patrón.
function msgcontains(txt, str)
	local start, len = 1, string.len(txt)
	while true do
		local s, e = string.find(txt, str, start, true)
		if s == nil then
			return false
		end
		local before = s == 1 or not string.find(string.sub(txt, s - 1, s - 1), '%w')
		local after = e == len or not string.find(string.sub(txt, e + 1, e + 1), '%w')
		if before and after then
			return true
		end
		start = s + 1
	end
end

function moveToPosition(x, y, z)
	selfMoveTo(x, y, z)
end

function moveToCreature(id)
	local tx, ty, tz = nil, nil, nil
	if id ~= 0 and id ~= nil then
		tx, ty, tz = creatureGetPosition(id)
	end
	if tx == nil then
		selfGotoIdle()
	else
		moveToPosition(tx, ty, tz)
	end
end

function selfGotoIdle()
	following = false
	attacking = false
	selfAttackCreature(0)
	target = 0
end
