-- Base: distancia al jugador, movimiento y coincidencia de palabras.
-- Parte de lib/npc.lua (ver docs/gameplay/NPC_SYSTEM.md).

function getDistanceToCreature(id)
	if id == 0 or id == nil then
		selfGotoIdle()
	end
	cx, cy, cz = creatureGetPosition(id)
	if cx == nil then
		return nil
	end
	sx, sy, sz = selfGetPosition()
	return math.max(math.abs(sx-cx), math.abs(sy-cy))
end

function msgcontains(txt, str)
	return (string.find(txt, str) and not string.find(txt, '(%w+)' .. str) and not string.find(txt, str .. '(%w+)'))
end

function moveToPosition(x, y, z)
	selfMoveTo(x, y, z)
end

function moveToCreature(id)
	if id == 0 or id == nil then
		selfGotoIdle()
	end
	tx, ty, tz = creatureGetPosition(id)
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
