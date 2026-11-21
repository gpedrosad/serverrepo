-- El Crisol v3: palancas 7200 Bronce / 7201 Plata / 7202 Oro / 7203 Info.
-- Ver docs/gameplay/CRUCIBLE.md. Textos ASCII (cliente 7.6).
--
-- Cada puerta es independiente (3 grupos pueden correr a la vez):
--   * La arena esta ocupada mientras haya un jugador adentro (no se guarda dueno).
--   * Entran juntos el que tira y los jugadores parados en la plataforma 3x2 de esa
--     puerta, hasta tantos como puntos de llegada tenga la arena.
--   * Si quedaron monstruos de una corrida abandonada, se completa hasta el tope
--     (PACK_COUNT + 1); nunca se apilan mas.

-- BEGIN LAYOUT (generado por scripts/map/generate-crucible.py)
HUB = {x0 = 600, y0 = 100, x1 = 610, y1 = 107, z = 0}
PADS = {
	bronze = {x0 = 600, y0 = 101, x1 = 602, y1 = 102, z = 0},
	silver = {x0 = 604, y0 = 101, x1 = 606, y1 = 102, z = 0},
	gold = {x0 = 608, y0 = 101, x1 = 610, y1 = 102, z = 0},
}
ARENAS = {
	bronze = {
		name = "Sand Pit", x0 = 615, y0 = 100, x1 = 625, y1 = 108, z = 0,
		-- arrivals[1] = el que tira; la cantidad es el tope del grupo
		arrivals = {{x = 620, y = 106, z = 0}, {x = 619, y = 106, z = 0}, {x = 621, y = 106, z = 0}, {x = 620, y = 105, z = 0}, {x = 619, y = 105, z = 0}, {x = 621, y = 105, z = 0}, {x = 618, y = 106, z = 0}},
		-- spawns[1] = elite/boss; el resto, pack
		spawns = {{x = 620, y = 101, z = 0}, {x = 618, y = 102, z = 0}, {x = 622, y = 102, z = 0}, {x = 616, y = 101, z = 0}, {x = 624, y = 101, z = 0}, {x = 619, y = 103, z = 0}, {x = 621, y = 103, z = 0}},
	},
	silver = {
		name = "Stone Coliseum", x0 = 630, y0 = 100, x1 = 640, y1 = 108, z = 0,
		-- arrivals[1] = el que tira; la cantidad es el tope del grupo
		arrivals = {{x = 635, y = 106, z = 0}, {x = 634, y = 106, z = 0}, {x = 636, y = 106, z = 0}, {x = 635, y = 105, z = 0}, {x = 634, y = 105, z = 0}, {x = 636, y = 105, z = 0}, {x = 633, y = 106, z = 0}},
		-- spawns[1] = elite/boss; el resto, pack
		spawns = {{x = 635, y = 101, z = 0}, {x = 633, y = 102, z = 0}, {x = 637, y = 102, z = 0}, {x = 631, y = 101, z = 0}, {x = 639, y = 101, z = 0}, {x = 634, y = 103, z = 0}, {x = 636, y = 103, z = 0}},
	},
	gold = {
		name = "Throne of Fire", x0 = 645, y0 = 100, x1 = 655, y1 = 108, z = 0,
		-- arrivals[1] = el que tira; la cantidad es el tope del grupo
		arrivals = {{x = 650, y = 106, z = 0}, {x = 649, y = 106, z = 0}, {x = 651, y = 106, z = 0}, {x = 650, y = 105, z = 0}, {x = 649, y = 105, z = 0}, {x = 651, y = 105, z = 0}, {x = 648, y = 106, z = 0}},
		-- spawns[1] = elite/boss; el resto, pack
		spawns = {{x = 650, y = 101, z = 0}, {x = 648, y = 102, z = 0}, {x = 652, y = 102, z = 0}, {x = 646, y = 101, z = 0}, {x = 654, y = 101, z = 0}, {x = 649, y = 103, z = 0}, {x = 651, y = 103, z = 0}},
	},
}
-- END LAYOUT

UID_INFO = 7203
DOORS = {[7200] = "bronze", [7201] = "silver", [7202] = "gold"}
DOOR_ORDER = {"bronze", "silver", "gold"}
DOOR_LABEL = {bronze = "Bronze", silver = "Silver", gold = "Gold"}

-- Rotacion diaria: elite de cada puerta y rare exclusivo del boss de Oro.
DAILY = {
	{bronze = "Minotaur Guard", silver = "Beholder", gold = "Crucible Ashlord", rare = "ashlord emberblade"},
	{bronze = "Cyclops", silver = "Demon Skeleton", gold = "Crucible Frostwarden", rare = "frostwarden chillblade"},
	{bronze = "Dwarf Guard", silver = "Vampire", gold = "Crucible Bonepriest", rare = "bonepriest reaver"},
	{bronze = "Minotaur Mage", silver = "Hero", gold = "Crucible Ironhide", rare = "ironhide crusher"},
	{bronze = "Beholder", silver = "Dragon", gold = "Crucible Venomqueen", rare = "venomqueen fang"},
	{bronze = "Giant Spider", silver = "Black Knight", gold = "Crucible Stormcaller", rare = "stormcaller maul"},
	{bronze = "Vampire", silver = "Warlock", gold = "Crucible Bloodreaver", rare = "bloodreaver saber"},
}

PACKS = {
	bronze = {"Minotaur", "Minotaur Archer", "Minotaur Guard"},
	silver = {"Demon Skeleton", "Ghoul", "Beholder", "Stalker"},
	gold = {"Dragon", "Giant Spider", "Hero", "Necromancer"},
}
PACK_COUNT = {bronze = 3, silver = 4, gold = 5}

MSG = 22 -- MSG_INFO
EFFECT_TELEPORT = 11

-------------------------------------------------------------------- utilidades

local function dayIndex()
	local day = tonumber(os.date("%j")) or 1
	return math.fmod(day - 1, table.getn(DAILY)) + 1
end

local function inBox(pos, box)
	return pos ~= nil and pos.z == box.z
		and pos.x >= box.x0 and pos.x <= box.x1
		and pos.y >= box.y0 and pos.y <= box.y1
end

-- {players = {uid...}, monsters = n}: criaturas dentro de una caja.
local function scan(box)
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

local function names(list)
	local out = {}
	for _, uid in ipairs(list) do
		table.insert(out, getPlayerName(uid) or "?")
	end
	return table.concat(out, ", ")
end

-- El que tira + los de la plataforma (sin repetir), hasta `max`. Devuelve grupo y los que no entran.
local function padGroup(cid, door, max)
	local group, left = {cid}, {}
	local seen = {[getPlayerName(cid)] = true}
	for _, uid in ipairs(scan(PADS[door]).players) do
		local name = getPlayerName(uid)
		if name and not seen[name] then
			seen[name] = true
			if table.getn(group) < max then
				table.insert(group, uid)
			else
				table.insert(left, uid)
			end
		end
	end
	return group, left
end

-- Invoca elite + pack hasta completar el tope. Devuelve cuantos aparecieron.
local function spawn(door, elite, existing)
	local spots = ARENAS[door].spawns
	local missing = PACK_COUNT[door] + 1 - existing
	local pack = PACKS[door]
	local ok = 0
	for i = 1, table.getn(spots) do
		if ok >= missing then
			break
		end
		local name = elite
		if i > 1 then
			name = pack[math.fmod(i - 2, table.getn(pack)) + 1]
		end
		if doSummonCreature(name, spots[i]) ~= 0 then
			ok = ok + 1
		end
	end
	return ok
end

-------------------------------------------------------------------- palancas

local function startDoor(cid, door)
	if not inBox(getPlayerPosition(cid), HUB) then
		doPlayerSendCancel(cid, "Use the lever from the Crucible Hall.")
		return
	end

	local arena = ARENAS[door]
	local inside = scan(arena)
	if table.getn(inside.players) > 0 then
		doPlayerSendCancel(cid, "Arena occupied by " .. names(inside.players) .. ".")
		return
	end

	local elite = DAILY[dayIndex()][door]
	local spawned = spawn(door, elite, inside.monsters)
	local total = inside.monsters + spawned
	if total == 0 then
		doPlayerSendCancel(cid, "Could not summon monsters. Please contact a GM.")
		return
	end

	local group, left = padGroup(cid, door, table.getn(arena.arrivals))
	local text = "Crucible " .. DOOR_LABEL[door] .. " (" .. arena.name .. "): " .. total ..
		" monsters, today's elite: " .. elite .. ". Exit: southern portal."
	for i, uid in ipairs(group) do
		doTeleportThing(uid, arena.arrivals[i])
		doPlayerSendTextMessage(uid, MSG, text)
	end
	doSendMagicEffect(arena.arrivals[1], EFFECT_TELEPORT)

	if inside.monsters > 0 then
		doPlayerSendTextMessage(cid, MSG, "There were " .. inside.monsters .. " monsters left from an abandoned run.")
	end
	if table.getn(group) > 1 then
		doPlayerSendTextMessage(cid, MSG, "Group: " .. names(group) .. ".")
	end
	for _, uid in ipairs(left) do
		doPlayerSendCancel(uid, "Group full (max " .. table.getn(arena.arrivals) .. "). Wait for the next run.")
	end
end

local function showInfo(cid)
	local today = DAILY[dayIndex()]
	doPlayerSendTextMessage(cid, MSG, "The Crucible - day #" .. dayIndex() .. ". Today's rare (Gold only): " .. today.rare .. ".")
	for _, door in ipairs(DOOR_ORDER) do
		local s = scan(ARENAS[door])
		local state = "free"
		if table.getn(s.players) > 0 then
			state = "occupied (" .. names(s.players) .. ", " .. s.monsters .. " monsters)"
		elseif s.monsters > 0 then
			state = "free, with " .. s.monsters .. " roaming monsters"
		end
		doPlayerSendTextMessage(cid, MSG, DOOR_LABEL[door] .. ": " .. today[door] .. " - " .. state .. ".")
	end
	doPlayerSendTextMessage(cid, MSG, "To enter as a group, stand on the platform in front of the lever (max "
		.. table.getn(ARENAS.gold.arrivals) .. ").")
end

function onUse(cid, item, frompos, item2, topos)
	if item.uid == UID_INFO then
		showInfo(cid)
		return 1
	end
	local door = DOORS[item.uid]
	if door then
		startDoor(cid, door)
		return 1
	end
	return 0
end
