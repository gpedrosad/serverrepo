-- Wave Arena v2 "Claro de la Selva". Ver docs/gameplay/WAVE_ARENA.md. Textos ASCII (cliente 7.6).
--
-- Palancas:
--   7100 campamento: entra el grupo (el que tira + los de la plataforma 3x2) y arranca la oleada 1.
--   7101 campamento: ranking semanal + tu marca + estado del claro.
--   7102 claro: siguiente oleada. Solo con la sala limpia; anota la oleada limpia a todos los del claro.
--   7103 claro: retirarse al campamento guardando la ultima oleada limpia.
--
-- Reglas:
--   * Una corrida a la vez; el claro esta ocupado mientras haya un jugador adentro (no hay dueno
--     guardado que pueda quedar colgado). Si el grupo muere o se retira entero, otro puede entrar.
--   * La marca cuenta oleadas LIMPIAS, no empezadas.
--   * Cada oleada escala con los jugadores en el claro; los jefes no se multiplican.
--   * Premio la primera vez en la semana que un jugador limpia la oleada 5 / 10 / 15 / 20.

-- BEGIN LAYOUT (generado por scripts/map/generate-wave-arena.py)
ARENA = {x0 = 170, y0 = 385, x1 = 182, y1 = 395, z = 7}
CAMP = {x0 = 172, y0 = 400, x1 = 180, y1 = 404, z = 7}
PAD = {x0 = 175, y0 = 401, x1 = 177, y1 = 402, z = 7}
CAMP_LANDING = {x = 176, y = 403, z = 7}
-- ARRIVALS[1] = el que tira; la cantidad es el tope del grupo
ARRIVALS = {{x = 176, y = 394, z = 7}, {x = 175, y = 394, z = 7}, {x = 177, y = 394, z = 7}, {x = 176, y = 393, z = 7}, {x = 175, y = 393, z = 7}, {x = 177, y = 393, z = 7}, {x = 174, y = 394, z = 7}}
-- SPAWNS[1] = jefe; el resto en orden de reparto
SPAWNS = {{x = 176, y = 386, z = 7}, {x = 173, y = 385, z = 7}, {x = 179, y = 385, z = 7}, {x = 170, y = 388, z = 7}, {x = 182, y = 388, z = 7}, {x = 175, y = 385, z = 7}, {x = 177, y = 385, z = 7}, {x = 170, y = 390, z = 7}, {x = 182, y = 390, z = 7}, {x = 172, y = 386, z = 7}, {x = 180, y = 386, z = 7}, {x = 174, y = 387, z = 7}, {x = 178, y = 387, z = 7}, {x = 170, y = 392, z = 7}, {x = 182, y = 392, z = 7}, {x = 176, y = 388, z = 7}}
-- END LAYOUT

UID_START, UID_RANK, UID_NEXT, UID_RETIRE = 7100, 7101, 7102, 7103

STORAGE_WEEK = 9300       -- semana de las marcas guardadas
STORAGE_BEST_WEEK = 9301  -- mejor oleada limpia de la semana
STORAGE_BEST_ALL = 9302   -- mejor oleada limpia historica
STORAGE_RUN_WAVE = 9303   -- oleada en curso de la corrida (respaldo si se recarga el script)
STORAGE_REWARD = 9310     -- 9310 + i: semana en que cobro el premio REWARDS[i]

RANK_FILE = "data/logs/wave_arena_rank.json"
MAX_RANK = 10
MSG = 22 -- MSG_INFO
EFFECT_TELEPORT, EFFECT_WAVE = 11, 12

-- {boss = jefe (no escala), pack = {{nombre, cantidad base}, ...}}
WAVES = {
	{pack = {{"Rat", 3}, {"Cave Rat", 2}}},
	{pack = {{"Wolf", 3}, {"Snake", 2}}},
	{pack = {{"Hyaena", 2}, {"Poison Spider", 2}}},
	{pack = {{"Centipede", 2}, {"Larva", 2}, {"Scorpion", 1}}},
	{boss = "Tarantula", pack = {{"Poison Spider", 3}}},
	{pack = {{"Orc Spearman", 2}, {"Orc Warrior", 2}}},
	{pack = {{"Bandit", 2}, {"Smuggler", 2}}},
	{pack = {{"War Wolf", 3}, {"Bear", 1}}},
	{pack = {{"Amazon", 2}, {"Valkyrie", 2}}},
	{boss = "Orc Leader", pack = {{"Orc Berserker", 1}, {"Orc Shaman", 2}}},
	{pack = {{"Lion", 2}, {"Tiger", 2}}},
	{pack = {{"Dworc Fleshhunter", 2}, {"Dworc Venomsniper", 2}, {"Dworf Voodoomaster", 1}}},
	{pack = {{"Stalker", 2}, {"Hunter", 2}}},
	{pack = {{"Terror Bird", 2}, {"Crocodile", 2}}},
	{boss = "Lizard Templar", pack = {{"Kongra", 2}, {"Sibang", 1}}},
	{pack = {{"Mummy", 2}, {"Ghoul", 2}}},
	{pack = {{"Carniphila", 2}, {"Lizard Sentinel", 2}}},
	{pack = {{"Gazer", 2}, {"Lizard Snakecharmer", 1}, {"Assassin", 2}}},
	{pack = {{"Blue Djinn", 2}, {"Lizard Templar", 1}}},
	{boss = "Giant Spider", pack = {{"Tarantula", 2}}},
}

-- Premio por oleada limpia, una vez por semana por jugador: {oleada, itemid, cantidad, texto}
REWARDS = {
	{5, 2152, 5, "5 platinum coins"},
	{10, 2152, 15, "15 platinum coins"},
	{15, 2152, 30, "30 platinum coins"},
	{20, 2160, 1, "1 crystal coin"},
}

-- Oleada en curso (0 = sin corrida). Se pierde al recargar: se recupera de STORAGE_RUN_WAVE.
if not WaveRun then
	WaveRun = {wave = 0}
end

-------------------------------------------------------------------- utilidades

local function weekId()
	return tonumber(os.date("%Y%W"))
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

local function tellAll(list, text)
	for _, uid in ipairs(list) do
		doPlayerSendTextMessage(uid, MSG, text)
	end
end

local function storage(uid, key)
	local v = getPlayerStorageValue(uid, key)
	if v < 0 then
		return 0
	end
	return v
end

-- El que tira + los de la plataforma (sin repetir), hasta `max`. Devuelve grupo y los que no entran.
local function padGroup(cid, max)
	local group, left = {cid}, {}
	local seen = {[getPlayerName(cid)] = true}
	for _, uid in ipairs(scan(PAD).players) do
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

-------------------------------------------------------------------- ranking (archivo JSON simple)

local function rankLoad()
	local data = {week = weekId(), scores = {}}
	local f = io.open(RANK_FILE, "r")
	if not f then
		return data
	end
	local raw = f:read("*a")
	f:close()
	if tonumber(string.match(raw, '"week"%s*:%s*(%d+)')) ~= data.week then
		return data
	end
	local block = string.match(raw, '"scores"%s*:%s*%{(.-)%}')
	if block then
		for name, score in string.gmatch(block, '"([^"]+)"%s*:%s*(%d+)') do
			data.scores[name] = tonumber(score)
		end
	end
	return data
end

local function rankSorted(data)
	local list = {}
	for n, s in pairs(data.scores) do
		table.insert(list, {name = n, score = s})
	end
	table.sort(list, function(a, b)
		if a.score == b.score then
			return a.name < b.name
		end
		return a.score > b.score
	end)
	return list
end

local function rankSave(name, score)
	if not name or score < 1 then
		return
	end
	local data = rankLoad()
	if score <= (data.scores[name] or 0) then
		return
	end
	data.scores[name] = score
	local list = rankSorted(data)
	local parts = {}
	for i = 1, math.min(MAX_RANK, table.getn(list)) do
		table.insert(parts, '    "' .. list[i].name .. '": ' .. list[i].score)
	end
	local f = io.open(RANK_FILE, "w")
	if f then
		f:write('{\n  "week": ' .. data.week .. ',\n  "scores": {\n' .. table.concat(parts, ",\n") .. "\n  }\n}\n")
		f:close()
	end
end

-------------------------------------------------------------------- marcas y premios

local function ensureWeek(uid)
	if storage(uid, STORAGE_WEEK) ~= weekId() then
		setPlayerStorageValue(uid, STORAGE_WEEK, weekId())
		setPlayerStorageValue(uid, STORAGE_BEST_WEEK, 0)
	end
end

-- Anota `cleared` oleadas limpias para uid: marca semanal/historica, ranking y premios.
local function record(uid, cleared)
	if cleared < 1 then
		return
	end
	ensureWeek(uid)
	if cleared > storage(uid, STORAGE_BEST_WEEK) then
		setPlayerStorageValue(uid, STORAGE_BEST_WEEK, cleared)
		rankSave(getPlayerName(uid), cleared)
	end
	if cleared > storage(uid, STORAGE_BEST_ALL) then
		setPlayerStorageValue(uid, STORAGE_BEST_ALL, cleared)
	end
	for i, r in ipairs(REWARDS) do
		if cleared >= r[1] and storage(uid, STORAGE_REWARD + i - 1) ~= weekId() then
			setPlayerStorageValue(uid, STORAGE_REWARD + i - 1, weekId())
			doPlayerAddItem(uid, r[2], r[3])
			doPlayerSendTextMessage(uid, MSG, "Premio semanal por limpiar la oleada " .. r[1] .. ": " .. r[4] .. ".")
		end
	end
end

-------------------------------------------------------------------- oleadas

local function scaled(count, players)
	return count + math.floor(count * (players - 1) / 2)
end

local function describe(n, players)
	local w = WAVES[n]
	local parts = {}
	if w.boss then
		table.insert(parts, "JEFE " .. w.boss)
	end
	for _, p in ipairs(w.pack) do
		table.insert(parts, scaled(p[2], players) .. " " .. p[1])
	end
	return "Oleada " .. n .. "/" .. table.getn(WAVES) .. ": " .. table.concat(parts, " + ")
end

-- Invoca la oleada n para `players` jugadores. Devuelve cuantos aparecieron.
local function spawnWave(n, players)
	local w = WAVES[n]
	local ok, spot = 0, 2
	if w.boss and doSummonCreature(w.boss, SPAWNS[1]) ~= 0 then
		ok = ok + 1
	end
	for _, p in ipairs(w.pack) do
		for _ = 1, scaled(p[2], players) do
			if doSummonCreature(p[1], SPAWNS[spot]) ~= 0 then
				ok = ok + 1
			end
			spot = spot + 1
			if spot > table.getn(SPAWNS) then
				spot = 2
			end
		end
	end
	return ok
end

local function setWave(n, players)
	WaveRun.wave = n
	for _, uid in ipairs(players) do
		setPlayerStorageValue(uid, STORAGE_RUN_WAVE, n)
	end
end

-- Oleada en curso; si el script se recargo, se recupera de los jugadores del claro.
local function currentWave(players)
	if WaveRun.wave == 0 then
		for _, uid in ipairs(players) do
			WaveRun.wave = math.max(WaveRun.wave, storage(uid, STORAGE_RUN_WAVE))
		end
	end
	return WaveRun.wave
end

local function launch(n, players)
	local got = spawnWave(n, table.getn(players))
	setWave(n, players)
	tellAll(players, describe(n, table.getn(players)) .. " (" .. got .. " invocados).")
	return got
end

-------------------------------------------------------------------- palancas

local function start(cid)
	if not inBox(getPlayerPosition(cid), CAMP) then
		doPlayerSendCancel(cid, "Usa la palanca desde el campamento.")
		return
	end
	local inside = scan(ARENA)
	if table.getn(inside.players) > 0 then
		doPlayerSendCancel(cid, "Corrida en curso de " .. names(inside.players) ..
			" (oleada " .. currentWave(inside.players) .. ").")
		return
	end

	local group, left = padGroup(cid, table.getn(ARRIVALS))
	for i, uid in ipairs(group) do
		doTeleportThing(uid, ARRIVALS[i])
	end
	doSendMagicEffect(ARRIVALS[1], EFFECT_TELEPORT)
	if inside.monsters > 0 then
		tellAll(group, "Quedaban " .. inside.monsters .. " monstruos de una corrida anterior: cuentan para la oleada 1.")
	end
	if launch(1, group) == 0 and inside.monsters == 0 then
		tellAll(group, "No se pudieron invocar monstruos. Avisa a un GM.")
	end
	if table.getn(group) > 1 then
		doPlayerSendTextMessage(cid, MSG, "Grupo: " .. names(group) .. ". Las oleadas escalan con el grupo.")
	end
	for _, uid in ipairs(left) do
		doPlayerSendCancel(uid, "Grupo lleno (max " .. table.getn(ARRIVALS) .. ").")
	end
end

local function nextWave(cid)
	if not inBox(getPlayerPosition(cid), ARENA) then
		return
	end
	local s = scan(ARENA)
	if s.monsters > 0 then
		doPlayerSendCancel(cid, "Quedan " .. s.monsters .. " monstruo(s). Limpien el claro primero.")
		return
	end
	local cleared = currentWave(s.players)
	if cleared > 0 and cleared < table.getn(WAVES) then
		tellAll(s.players, "Oleada " .. cleared .. " limpia.")
	end
	for _, uid in ipairs(s.players) do
		record(uid, cleared)
	end

	if cleared >= table.getn(WAVES) then
		tellAll(s.players, "Completaron las " .. table.getn(WAVES) .. " oleadas del Claro de la Selva!")
		for _, uid in ipairs(s.players) do
			setPlayerStorageValue(uid, STORAGE_RUN_WAVE, 0)
			doTeleportThing(uid, CAMP_LANDING)
		end
		doSendMagicEffect(CAMP_LANDING, EFFECT_TELEPORT)
		WaveRun.wave = 0
		return
	end
	launch(cleared + 1, s.players)
	doSendMagicEffect(getPlayerPosition(cid), EFFECT_WAVE)
end

local function retire(cid)
	if not inBox(getPlayerPosition(cid), ARENA) then
		return
	end
	local s = scan(ARENA)
	local wave = currentWave(s.players)
	local cleared = wave
	if s.monsters > 0 then
		cleared = wave - 1
	end
	record(cid, cleared)
	setPlayerStorageValue(cid, STORAGE_RUN_WAVE, 0)
	doTeleportThing(cid, CAMP_LANDING)
	doSendMagicEffect(CAMP_LANDING, EFFECT_TELEPORT)
	doPlayerSendTextMessage(cid, MSG, "Te retiraste con " .. math.max(cleared, 0) .. " oleada(s) limpias.")
	if table.getn(s.players) <= 1 then
		WaveRun.wave = 0
	end
end

local function showRank(cid)
	ensureWeek(cid)
	local data = rankLoad()
	doPlayerSendTextMessage(cid, MSG, "Wave Arena - ranking semana " .. data.week ..
		". Tu marca: " .. storage(cid, STORAGE_BEST_WEEK) .. " (semana) / " ..
		storage(cid, STORAGE_BEST_ALL) .. " (historica).")
	local list = rankSorted(data)
	if table.getn(list) == 0 then
		doPlayerSendTextMessage(cid, MSG, "Sin marcas esta semana. Se el primero!")
	end
	for i = 1, math.min(5, table.getn(list)) do
		doPlayerSendTextMessage(cid, MSG, i .. ") " .. list[i].name .. " - oleada " .. list[i].score)
	end
	local s = scan(ARENA)
	if table.getn(s.players) > 0 then
		doPlayerSendTextMessage(cid, MSG, "En el claro: " .. names(s.players) .. " (oleada " .. currentWave(s.players) .. ").")
	else
		doPlayerSendTextMessage(cid, MSG, "El claro esta libre.")
	end
end

function onUse(cid, item, frompos, item2, topos)
	if item.uid == UID_START then
		start(cid)
	elseif item.uid == UID_RANK then
		showRank(cid)
	elseif item.uid == UID_NEXT then
		nextWave(cid)
	elseif item.uid == UID_RETIRE then
		retire(cid)
	else
		return 0
	end
	return 1
end
