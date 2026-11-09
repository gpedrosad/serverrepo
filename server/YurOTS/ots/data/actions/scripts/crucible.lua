-- El Crisol v2: palancas 7200 Bronce / 7201 Plata / 7202 Oro / 7203 Info.
-- Ver docs/gameplay/CRUCIBLE.md. Textos ASCII (cliente 7.6).
--
-- Cada puerta es independiente (3 grupos pueden correr a la vez):
--   * La arena esta ocupada mientras haya un jugador adentro.
--   * Entran juntos todos los jugadores parados en la plataforma 3x2 de esa puerta
--     mas el que tira la palanca (max 7).
--   * Monstruos en la mitad norte; el grupo llega al sur, junto al TP de salida.
--   * Si quedaron monstruos de una corrida abandonada, se completan hasta el tope
--     (no se apilan infinitos).

UID_BRONZE = 7200
UID_SILVER = 7201
UID_GOLD = 7202
UID_INFO = 7203

-- BEGIN LAYOUT (generado por scripts/map/generate-crucible.py)
HUB = {x0 = 76, y0 = 79, x1 = 94, y1 = 95, z = 0}
HUB_LANDING = {x = 85, y = 92, z = 0}
PADS = {
	bronze = {x0 = 78, y0 = 80, x1 = 80, y1 = 81, z = 0},
	silver = {x0 = 84, y0 = 80, x1 = 86, y1 = 81, z = 0},
	gold = {x0 = 90, y0 = 80, x1 = 92, y1 = 81, z = 0},
}
ARENAS = {
	bronze = {
		name = "Foso de Arena",
		x0 = 104, y0 = 80, x1 = 118, y1 = 92, z = 0,
		entry = {x = 111, y = 90, z = 0},
		-- spawns[1] = elite/boss; el resto, pack
		spawns = {{x = 111, y = 82, z = 0}, {x = 107, y = 83, z = 0}, {x = 115, y = 83, z = 0}, {x = 109, y = 85, z = 0}, {x = 113, y = 85, z = 0}, {x = 106, y = 86, z = 0}, {x = 116, y = 86, z = 0}},
	},
	silver = {
		name = "Coliseo de Piedra",
		x0 = 128, y0 = 79, x1 = 144, y1 = 93, z = 0,
		entry = {x = 136, y = 91, z = 0},
		-- spawns[1] = elite/boss; el resto, pack
		spawns = {{x = 136, y = 81, z = 0}, {x = 132, y = 82, z = 0}, {x = 140, y = 82, z = 0}, {x = 134, y = 84, z = 0}, {x = 138, y = 84, z = 0}, {x = 130, y = 85, z = 0}, {x = 142, y = 85, z = 0}},
	},
	gold = {
		name = "Trono de Fuego",
		x0 = 154, y0 = 78, x1 = 172, y1 = 94, z = 0,
		entry = {x = 163, y = 92, z = 0},
		-- spawns[1] = elite/boss; el resto, pack
		spawns = {{x = 163, y = 80, z = 0}, {x = 158, y = 81, z = 0}, {x = 168, y = 81, z = 0}, {x = 161, y = 83, z = 0}, {x = 165, y = 83, z = 0}, {x = 156, y = 84, z = 0}, {x = 170, y = 84, z = 0}},
	},
}
-- END LAYOUT

DOORS = {[UID_BRONZE] = "bronze", [UID_SILVER] = "silver", [UID_GOLD] = "gold"}
DOOR_LABEL = {bronze = "Bronce", silver = "Plata", gold = "Oro"}

-- Por dia: elite bronce, elite plata, boss oro (custom), rare exclusivo del boss
DAILY = {
	{"Minotaur Guard", "Beholder", "Crucible Ashlord", "ashlord emberblade"},
	{"Cyclops", "Demon Skeleton", "Crucible Frostwarden", "frostwarden chillblade"},
	{"Dwarf Guard", "Vampire", "Crucible Bonepriest", "bonepriest reaver"},
	{"Minotaur Mage", "Hero", "Crucible Ironhide", "ironhide crusher"},
	{"Beholder", "Dragon", "Crucible Venomqueen", "venomqueen fang"},
	{"Giant Spider", "Black Knight", "Crucible Stormcaller", "stormcaller maul"},
	{"Vampire", "Warlock", "Crucible Bloodreaver", "bloodreaver saber"},
}
ELITE_INDEX = {bronze = 1, silver = 2, gold = 3}

PACKS = {
	bronze = {"Minotaur", "Minotaur Archer", "Minotaur Guard"},
	silver = {"Demon Skeleton", "Ghoul", "Beholder", "Stalker"},
	gold = {"Dragon", "Giant Spider", "Hero", "Necromancer"},
}
PACK_COUNT = {bronze = 3, silver = 4, gold = 5}

MSG = 22 -- MSG_INFO (texto blanco/verde en la consola)

-- Llegada del grupo: entrada y casillas vecinas (la fila de abajo es la del TP de salida, +2).
ARRIVAL = {{0, 0}, {-1, 0}, {1, 0}, {0, -1}, {-1, -1}, {1, -1}, {-2, 0}}

-------------------------------------------------------------------- utilidades

function crucibleDayIndex()
	local day = tonumber(os.date("%j")) or 1
	return math.fmod(day - 1, table.getn(DAILY)) + 1
end

function crucibleToday()
	return DAILY[crucibleDayIndex()]
end

function crucibleInBox(pos, box)
	return pos and pos.z == box.z
		and pos.x >= box.x0 and pos.x <= box.x1
		and pos.y >= box.y0 and pos.y <= box.y1
end

-- Lista {players = {uid...}, monsters = n} de las criaturas dentro de una caja.
function crucibleScan(box)
	local out = {players = {}, monsters = 0}
	for x = box.x0, box.x1 do
		for y = box.y0, box.y1 do
			local th = getThingfromPos({x = x, y = y, z = box.z, stackpos = 253})
			if th and th.itemid == 1 then
				if th.type == 1 then
					table.insert(out.players, th.uid)
				elseif th.type == 2 then
					out.monsters = out.monsters + 1
				end
			end
		end
	end
	return out
end

-- Jugadores parados en la plataforma de la puerta (incluye al que tira si esta encima).
function crucibleGroup(cid, door)
	local group = {cid}
	local seen = {}
	seen[getPlayerName(cid)] = true
	for _, uid in ipairs(crucibleScan(PADS[door]).players) do
		local name = getPlayerName(uid)
		if name and not seen[name] then
			seen[name] = true
			table.insert(group, uid)
		end
	end
	return group
end

function crucibleNames(group)
	local names = {}
	for _, uid in ipairs(group) do
		table.insert(names, getPlayerName(uid))
	end
	return table.concat(names, ", ")
end

-------------------------------------------------------------------- puertas

function crucibleSpawn(door, elite, existing)
	local arena = ARENAS[door]
	local spots = arena.spawns
	local target = PACK_COUNT[door] + 1
	local missing = target - existing
	if missing <= 0 then
		return 0
	end
	local ok = 0
	-- el elite/boss siempre arriba al centro; despues el pack en el resto de los puntos
	if doSummonCreature(elite, spots[1]) ~= 0 then
		ok = ok + 1
	end
	local pack = PACKS[door]
	local i = 1
	while ok < missing and i <= table.getn(spots) - 1 do
		local name = pack[math.fmod(i - 1, table.getn(pack)) + 1]
		if doSummonCreature(name, spots[i + 1]) ~= 0 then
			ok = ok + 1
		end
		i = i + 1
	end
	return ok
end

function crucibleStartDoor(cid, door)
	if not crucibleInBox(getPlayerPosition(cid), HUB) then
		doPlayerSendCancel(cid, "Usa la palanca desde la Sala del Crisol.")
		return
	end

	local arena = ARENAS[door]
	local inside = crucibleScan(arena)
	if table.getn(inside.players) > 0 then
		doPlayerSendCancel(cid, "Arena ocupada por " .. crucibleNames(inside.players) .. ".")
		return
	end

	local today = crucibleToday()
	local elite = today[ELITE_INDEX[door]]
	local spawned = crucibleSpawn(door, elite, inside.monsters)
	if spawned == 0 and inside.monsters == 0 then
		doPlayerSendCancel(cid, "No se pudieron invocar monstruos. Avisa a un GM.")
		return
	end

	local group = crucibleGroup(cid, door)
	local total = inside.monsters + spawned
	for i, uid in ipairs(group) do
		local off = ARRIVAL[math.fmod(i - 1, table.getn(ARRIVAL)) + 1]
		doTeleportThing(uid, {x = arena.entry.x + off[1], y = arena.entry.y + off[2], z = arena.entry.z})
		doPlayerSendTextMessage(uid, MSG,
			"Crisol " .. DOOR_LABEL[door] .. " (" .. arena.name .. "): " .. total ..
			" monstruos, elite de hoy " .. elite .. ". Salida: TP al sur.")
	end
	doSendMagicEffect(arena.entry, 11)
	if inside.monsters > 0 then
		doPlayerSendTextMessage(cid, MSG,
			"Quedaban " .. inside.monsters .. " monstruos de una corrida abandonada.")
	end
	if table.getn(group) > 1 then
		doPlayerSendTextMessage(cid, MSG, "Grupo: " .. crucibleNames(group) .. ".")
	end
end

function crucibleShowInfo(cid)
	local today = crucibleToday()
	doPlayerSendTextMessage(cid, MSG, "El Crisol - dia #" .. crucibleDayIndex() ..
		". Rare de hoy (solo Oro): " .. today[4] .. ".")
	for _, door in ipairs({"bronze", "silver", "gold"}) do
		local s = crucibleScan(ARENAS[door])
		local state
		if table.getn(s.players) > 0 then
			state = "ocupada (" .. crucibleNames(s.players) .. ", " .. s.monsters .. " monstruos)"
		elseif s.monsters > 0 then
			state = "libre, con " .. s.monsters .. " monstruos sueltos"
		else
			state = "libre"
		end
		doPlayerSendTextMessage(cid, MSG, DOOR_LABEL[door] .. ": " .. today[ELITE_INDEX[door]] ..
			" - " .. state .. ".")
	end
	doPlayerSendTextMessage(cid, MSG, "Para entrar en grupo, paren en la plataforma frente a la palanca.")
end

function onUse(cid, item, frompos, item2, topos)
	if item.uid == UID_INFO then
		crucibleShowInfo(cid)
		return 1
	end
	local door = DOORS[item.uid]
	if door then
		crucibleStartDoor(cid, door)
		return 1
	end
	return 0
end
