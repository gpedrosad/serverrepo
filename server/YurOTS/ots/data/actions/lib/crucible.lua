-- El Crisol v4: configuración compartida entre las palancas (data/actions/scripts/crucible.lua)
-- y el guardián Varkon (data/npc/scripts/crucible_warden.lua). Ver docs/gameplay/CRUCIBLE.md.
-- Textos visibles en inglés y ASCII (cliente 7.6).
--
-- Escalera diaria: Bronze -> Silver -> Gold. Limpiar una puerta abre la siguiente ese día y da su
-- premio una vez por día. El jefe de Oro se puede matar una vez por día por jugador.
-- Las palancas solo validan y mandan al grupo; Varkon corre la pelea (spawn, HUD, premio, limpieza).

CRUCIBLE = {}

-- BEGIN LAYOUT (generado por scripts/map/generate-crucible.py)
CRUCIBLE.hub = {x0 = 600, y0 = 100, x1 = 610, y1 = 107, z = 0}
CRUCIBLE.landing = {x = 605, y = 105, z = 0}
CRUCIBLE.pads = {
	bronze = {x0 = 600, y0 = 101, x1 = 602, y1 = 102, z = 0},
	silver = {x0 = 604, y0 = 101, x1 = 606, y1 = 102, z = 0},
	gold = {x0 = 608, y0 = 101, x1 = 610, y1 = 102, z = 0},
}
CRUCIBLE.arenas = {
	bronze = {
		name = "Sand Pit", x0 = 615, y0 = 100, x1 = 625, y1 = 108, z = 0,
		-- arrivals[1] = el que tira; la cantidad es el tope del grupo
		arrivals = {{x = 620, y = 106, z = 0}, {x = 619, y = 106, z = 0}, {x = 621, y = 106, z = 0}, {x = 620, y = 105, z = 0}, {x = 619, y = 105, z = 0}, {x = 621, y = 105, z = 0}, {x = 620, y = 107, z = 0}},
		-- spawns[1] = elite/jefe; el resto, la escolta
		spawns = {{x = 620, y = 101, z = 0}, {x = 618, y = 102, z = 0}, {x = 622, y = 102, z = 0}, {x = 616, y = 101, z = 0}, {x = 624, y = 101, z = 0}, {x = 619, y = 103, z = 0}, {x = 621, y = 103, z = 0}},
	},
	silver = {
		name = "Stone Coliseum", x0 = 630, y0 = 100, x1 = 640, y1 = 108, z = 0,
		-- arrivals[1] = el que tira; la cantidad es el tope del grupo
		arrivals = {{x = 635, y = 106, z = 0}, {x = 634, y = 106, z = 0}, {x = 636, y = 106, z = 0}, {x = 635, y = 105, z = 0}, {x = 634, y = 105, z = 0}, {x = 636, y = 105, z = 0}, {x = 635, y = 107, z = 0}},
		-- spawns[1] = elite/jefe; el resto, la escolta
		spawns = {{x = 635, y = 101, z = 0}, {x = 633, y = 102, z = 0}, {x = 637, y = 102, z = 0}, {x = 631, y = 101, z = 0}, {x = 639, y = 101, z = 0}, {x = 634, y = 103, z = 0}, {x = 636, y = 103, z = 0}},
	},
	gold = {
		name = "Throne of Fire", x0 = 645, y0 = 100, x1 = 655, y1 = 108, z = 0,
		-- arrivals[1] = el que tira; la cantidad es el tope del grupo
		arrivals = {{x = 650, y = 106, z = 0}, {x = 649, y = 106, z = 0}, {x = 651, y = 106, z = 0}, {x = 650, y = 105, z = 0}, {x = 649, y = 105, z = 0}, {x = 651, y = 105, z = 0}, {x = 650, y = 107, z = 0}},
		-- spawns[1] = elite/jefe; el resto, la escolta
		spawns = {{x = 650, y = 101, z = 0}, {x = 648, y = 102, z = 0}, {x = 652, y = 102, z = 0}, {x = 646, y = 101, z = 0}, {x = 654, y = 101, z = 0}, {x = 649, y = 103, z = 0}, {x = 651, y = 103, z = 0}},
	},
}
-- END LAYOUT

CRUCIBLE.order = {"bronze", "silver", "gold"}

-- step = lugar en la escalera; level = recomendado (solo informativo, está en los carteles).
-- escort = monstruos que acompañan al elite/jefe (se reparten en rueda hasta escortCount).
CRUCIBLE.tiers = {
	bronze = {step = 1, label = "Bronze", level = 30, escortCount = 3,
		escort = {"Minotaur", "Minotaur Archer", "Minotaur Guard"},
		reward = {gold = 2000, exp = 5000, gems = 1}},
	silver = {step = 2, label = "Silver", level = 50, escortCount = 4,
		escort = {"Demon Skeleton", "Ghoul", "Beholder", "Stalker"},
		reward = {gold = 5000, exp = 15000, gems = 2}},
	gold = {step = 3, label = "Gold", level = 80, escortCount = 5,
		escort = {"Dragon", "Giant Spider", "Hero", "Necromancer"},
		reward = {gold = 10000, exp = 40000, gems = 3}},
}

-- Rotación de 7 días. Elites con vida creciente por puerta: Bronze ~400-580, Silver ~900-1400,
-- Gold = jefe propio con su arma exclusiva (data/monster/crucible *.xml).
CRUCIBLE.daily = {
	{bronze = "Orc Leader", silver = "Giant Spider", gold = "Crucible Ashlord", rare = "ashlord emberblade"},
	{bronze = "Cyclops Smith", silver = "Dragon", gold = "Crucible Frostwarden", rare = "frostwarden chillblade"},
	{bronze = "Dwarf Geomancer", silver = "Lich", gold = "Crucible Bonepriest", rare = "bonepriest reaver"},
	{bronze = "Vampire", silver = "Hero", gold = "Crucible Ironhide", rare = "ironhide crusher"},
	{bronze = "Lizard Templar", silver = "Vampire Bride", gold = "Crucible Venomqueen", rare = "venomqueen fang"},
	{bronze = "Bone Beast", silver = "Undead Gladiator", gold = "Crucible Stormcaller", rare = "stormcaller maul"},
	{bronze = "Necromancer", silver = "Orc Warlord", gold = "Crucible Bloodreaver", rare = "bloodreaver saber"},
}

CRUCIBLE.SMALL_GEMS = {
	{2145, "small diamond"}, {2146, "small sapphire"}, {2147, "small ruby"},
	{2149, "small emerald"}, {2150, "small amethyst"},
}

-- Storage del jugador (9500-9504)
CRUCIBLE.STORAGE_DAY = 9500        -- día (crucibleDay) al que corresponde STEP
CRUCIBLE.STORAGE_STEP = 9501       -- última puerta limpiada ese día: 0 ninguna, 1 Bronze, 2 Silver, 3 Gold
CRUCIBLE.STORAGE_BOSS_DAY = 9502   -- día en que mató al jefe de Oro (una vez por día)
CRUCIBLE.STORAGE_TICKET_STEP = 9503 -- puerta por la que entró con la palanca (1-3)
CRUCIBLE.STORAGE_TICKET_TIME = 9504 -- os.time() de esa entrada; Varkon saca a quien no tenga pase
CRUCIBLE.TICKET_SEC = 60

-------------------------------------------------------------------- utilidades

-- Día local monótono (no se corta en Año Nuevo como os.date("%j")).
function crucibleDay()
	local now = os.time()
	local offset = os.time(os.date("*t", now)) - os.time(os.date("!*t", now))
	return math.floor((now + offset) / 86400)
end

function crucibleDayIndex()
	return math.fmod(crucibleDay(), table.getn(CRUCIBLE.daily)) + 1
end

function crucibleToday()
	return CRUCIBLE.daily[crucibleDayIndex()]
end

function crucibleInBox(x, y, z, box)
	return x ~= nil and z == box.z and x >= box.x0 and x <= box.x1 and y >= box.y0 and y <= box.y1
end

local function storage(uid, key)
	local v = getPlayerStorageValue(uid, key)
	if v == nil or v < 0 then
		return 0
	end
	return v
end

-- Puertas limpiadas hoy (0-3).
function crucibleStep(uid)
	if storage(uid, CRUCIBLE.STORAGE_DAY) ~= crucibleDay() then
		return 0
	end
	return storage(uid, CRUCIBLE.STORAGE_STEP)
end

function crucibleBossDone(uid)
	return storage(uid, CRUCIBLE.STORAGE_BOSS_DAY) == crucibleDay()
end

-- nil si puede entrar por esa puerta; si no, el motivo (texto para el jugador).
function crucibleEntryError(uid, door)
	local tier = CRUCIBLE.tiers[door]
	if tier.step > 1 and crucibleStep(uid) < tier.step - 1 then
		local prev = CRUCIBLE.tiers[CRUCIBLE.order[tier.step - 1]].label
		return "the " .. tier.label .. " gate opens after you clear the " .. prev .. " gate today."
	end
	if door == "gold" and crucibleBossDone(uid) then
		return "you already defeated today's Gold boss. Come back tomorrow."
	end
	return nil
end

-- Marca la puerta como limpiada hoy. true si es la primera vez hoy (corresponde premio).
function crucibleMarkCleared(uid, door)
	local step = CRUCIBLE.tiers[door].step
	local before = crucibleStep(uid)
	setPlayerStorageValue(uid, CRUCIBLE.STORAGE_DAY, crucibleDay())
	if step > before then
		setPlayerStorageValue(uid, CRUCIBLE.STORAGE_STEP, step)
		return true
	end
	setPlayerStorageValue(uid, CRUCIBLE.STORAGE_STEP, before)
	return false
end

function crucibleGiveTicket(uid, door)
	setPlayerStorageValue(uid, CRUCIBLE.STORAGE_TICKET_STEP, CRUCIBLE.tiers[door].step)
	setPlayerStorageValue(uid, CRUCIBLE.STORAGE_TICKET_TIME, os.time())
end

-- true (y lo consume) si entró por la palanca de esa puerta hace poco.
function crucibleUseTicket(uid, door)
	local ok = storage(uid, CRUCIBLE.STORAGE_TICKET_STEP) == CRUCIBLE.tiers[door].step
		and os.time() - storage(uid, CRUCIBLE.STORAGE_TICKET_TIME) <= CRUCIBLE.TICKET_SEC
	setPlayerStorageValue(uid, CRUCIBLE.STORAGE_TICKET_STEP, 0)
	return ok
end

function crucibleRewardText(door)
	local r = CRUCIBLE.tiers[door].reward
	local gems = "small gem"
	if r.gems > 1 then
		gems = "small gems"
	end
	return r.gold .. " gp, " .. r.exp .. " exp and " .. r.gems .. " " .. gems
end

-- "Bronze: done. Silver: open. Gold: locked." para el jugador.
function crucibleProgressText(uid)
	local step = crucibleStep(uid)
	local parts = {}
	for _, door in ipairs(CRUCIBLE.order) do
		local tier = CRUCIBLE.tiers[door]
		local state = "locked"
		if step >= tier.step then
			state = "cleared"
		elseif step == tier.step - 1 then
			state = "open"
		end
		if door == "gold" and crucibleBossDone(uid) and step < tier.step then
			state = "boss defeated"
		end
		table.insert(parts, tier.label .. ": " .. state)
	end
	return table.concat(parts, ". ") .. "."
end

function crucibleLineupText()
	local today = crucibleToday()
	return "Today (day " .. crucibleDayIndex() .. " of 7): Bronze elite " .. today.bronze
		.. ", Silver elite " .. today.silver .. ", Gold boss " .. today.gold
		.. " (may drop the " .. today.rare .. ")."
end
