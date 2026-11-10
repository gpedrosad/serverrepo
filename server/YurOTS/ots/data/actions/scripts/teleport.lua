-- Escaleras de mano, escaleras, trampillas y agujeros: "usar" (click derecho) lleva al piso de
-- arriba o de abajo. Ver docs/gameplay/STAIRS.md.
--
-- Al bajar se aterriza igual que bajando caminando (Game::thingMove en game.cpp): si en el piso
-- de abajo hay una escalera de subida, el jugador queda al costado de ella. Antes quedaba encima,
-- "en medio de la escalera" (puente principal 141-142,59 y 141-142,74, piso 6, y 26 más).

LADDERS_UP = {[1386] = true, [3678] = true}

-- Escaleras de subida (flags floorchange_* de items.otb) -> corrimiento {dx, dy} al aterrizar
-- abajo. North: la escalera sube hacia el norte, se aterriza al sur (y + 1); y así.
STAIRS_LANDING = {}
local function landing(ids, dx, dy)
	for i = 1, table.getn(ids) do
		STAIRS_LANDING[ids[i]] = {dx, dy}
	end
end
landing({1385, 1394, 1396, 1404, 3685, 3687}, 0, 1)	-- north
landing({1392, 1402, 3683}, 0, -1)			-- south
landing({1388, 1398, 3679}, -1, 0)			-- east
landing({1390, 1400, 3681, 3688}, 1, 0)			-- west
landing({1555}, -1, 1)					-- north + east
landing({1553}, 1, 1)					-- north + west
landing({1557}, -1, -1)					-- south + east
landing({1559}, 1, -1)					-- south + west

local function landingOffset(pos)
	for stackpos = 1, 10 do
		local thing = getThingfromPos({x = pos.x, y = pos.y, z = pos.z, stackpos = stackpos})
		if thing == nil or thing.itemid == 0 then
			break
		end
		local offset = STAIRS_LANDING[thing.itemid]
		if offset ~= nil then
			return offset[1], offset[2]
		end
	end
	return 0, 0
end

function onUse(cid, item, frompos, item2, topos)
	local npos = {x = frompos.x, y = frompos.y, z = frompos.z}
	if LADDERS_UP[item.itemid] then
		npos.y = npos.y + 1
		npos.z = npos.z - 1
	else
		npos.z = npos.z + 1
		local dx, dy = landingOffset(npos)
		npos.x = npos.x + dx
		npos.y = npos.y + dy
	end
	doTeleportThing(cid, npos)
	return 1
end
