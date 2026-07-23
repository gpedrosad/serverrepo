-- Wave Arena: palanca uniqueid 7100 (start/next) y 7101 (ranking semanal).
-- Tras limpiar la sala, usa la palanca para la siguiente oleada.
-- Textos en ASCII (cliente 7.6 no muestra bien acentos/signos raros).

UID_START = 7100
UID_RANK = 7101

STORAGE_WEEK = 9300
STORAGE_BEST_WEEK = 9301
STORAGE_BEST_ALL = 9302

ARENA = {x0 = 174, y0 = 386, x1 = 180, y1 = 392, z = 7}

RANK_FILE = "data/logs/wave_arena_rank.json"
MAX_RANK = 10

-- Oleadas: { nombre, cantidad } — progresión gradual.
WAVES = {
	{"Rat", 2},
	{"Cave Rat", 3},
	{"Hyaena", 2},
	{"Poison Spider", 3},
	{"Centipede", 3},
	{"Larva", 3},
	{"Scorpion", 3},
	{"Orc Spearman", 3},
	{"Bandit", 3},
	{"War Wolf", 3},
	{"Amazon", 3},
	{"Valkyrie", 3},
	{"Stalker", 3},
	{"Assassin", 3},
	{"Hunter", 3},
	{"Mummy", 3},
	{"Terror Bird", 3},
	{"Gazer", 3},
	{"Blue Djinn", 2},
	{"Blue Djinn", 3},
}

if not WaveArenaState then
	WaveArenaState = {
		wave = 0,
		owner = 0,
		ownerName = "",
	}
end

function waveWeekId()
	return tonumber(os.date("%Y%W"))
end

function waveEnsureWeek(cid)
	local week = waveWeekId()
	local stored = getPlayerStorageValue(cid, STORAGE_WEEK)
	if stored ~= week then
		setPlayerStorageValue(cid, STORAGE_WEEK, week)
		setPlayerStorageValue(cid, STORAGE_BEST_WEEK, 0)
	end
end

function waveUpdateBest(cid, wave)
	waveEnsureWeek(cid)
	local bestW = getPlayerStorageValue(cid, STORAGE_BEST_WEEK)
	if bestW < 0 then
		bestW = 0
	end
	if wave > bestW then
		setPlayerStorageValue(cid, STORAGE_BEST_WEEK, wave)
	end
	local bestA = getPlayerStorageValue(cid, STORAGE_BEST_ALL)
	if bestA < 0 then
		bestA = 0
	end
	if wave > bestA then
		setPlayerStorageValue(cid, STORAGE_BEST_ALL, wave)
	end
	waveRankSave(getPlayerName(cid), getPlayerStorageValue(cid, STORAGE_BEST_WEEK))
end

function waveRankLoad()
	local week = waveWeekId()
	local data = {week = week, scores = {}}
	local f = io.open(RANK_FILE, "r")
	if not f then
		return data
	end
	local raw = f:read("*a")
	f:close()
	local fileWeek = tonumber(string.match(raw, '"week"%s*:%s*(%d+)'))
	if fileWeek ~= week then
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

function waveRankSave(name, score)
	if not name or name == "" or score < 1 then
		return
	end
	local data = waveRankLoad()
	local prev = data.scores[name] or 0
	if score <= prev then
		return
	end
	data.scores[name] = score
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
	local n = math.min(MAX_RANK, table.getn(list))
	local parts = {}
	for i = 1, n do
		table.insert(parts, '    "' .. list[i].name .. '": ' .. list[i].score)
	end
	local f = io.open(RANK_FILE, "w")
	if f then
		f:write('{\n  "week": ' .. data.week .. ',\n  "scores": {\n')
		f:write(table.concat(parts, ",\n"))
		f:write("\n  }\n}\n")
		f:close()
	end
end

function waveRankMessage(cid)
	local data = waveRankLoad()
	waveEnsureWeek(cid)
	local mine = getPlayerStorageValue(cid, STORAGE_BEST_WEEK)
	if mine < 0 then
		mine = 0
	end
	local all = getPlayerStorageValue(cid, STORAGE_BEST_ALL)
	if all < 0 then
		all = 0
	end
	doPlayerSendTextMessage(cid, 22, "Wave Arena - ranking semana " .. data.week)
	doPlayerSendTextMessage(cid, 22, "Tu mejor: oleada " .. mine .. " (semana) / " .. all .. " (historico)")
	local list = {}
	for n, s in pairs(data.scores) do
		table.insert(list, {name = n, score = s})
	end
	table.sort(list, function(a, b)
		return a.score > b.score
	end)
	if table.getn(list) == 0 then
		doPlayerSendTextMessage(cid, 22, "Sin ranking esta semana. Se el primero!")
		return
	end
	local n = math.min(5, table.getn(list))
	for i = 1, n do
		doPlayerSendTextMessage(cid, 22, i .. ") " .. list[i].name .. " - oleada " .. list[i].score)
	end
end

function waveCountMonsters(cid)
	local count = 0
	for x = ARENA.x0, ARENA.x1 do
		for y = ARENA.y0, ARENA.y1 do
			local pos = {x = x, y = y, z = ARENA.z, stackpos = 253}
			local th = getThingfromPos(pos)
			-- Excluir al jugador que usa la palanca (stackpos 253 = creature).
			if th.itemid > 0 and th.uid ~= cid then
				count = count + 1
			end
		end
	end
	return count
end

function wavePlayerInArena(cid)
	local pos = getPlayerPosition(cid)
	if not pos then
		return false
	end
	return pos.z == ARENA.z
		and pos.x >= ARENA.x0 - 2
		and pos.x <= ARENA.x1 + 2
		and pos.y >= ARENA.y0 - 2
		and pos.y <= ARENA.y1 + 4
end

function waveSpawnOffsets(n)
	-- Posiciones relativas al centro de la arena
	local cx = math.floor((ARENA.x0 + ARENA.x1) / 2)
	local cy = math.floor((ARENA.y0 + ARENA.y1) / 2)
	local spots = {
		{0, 0}, {1, 0}, {-1, 0}, {0, 1}, {0, -1},
		{1, 1}, {-1, 1}, {1, -1}, {-1, -1}, {2, 0},
		{-2, 0}, {0, 2}, {0, -2}, {2, 1}, {-2, -1},
	}
	local out = {}
	for i = 1, n do
		local s = spots[((i - 1) % table.getn(spots)) + 1]
		local x = cx + s[1]
		local y = cy + s[2]
		if x < ARENA.x0 then x = ARENA.x0 end
		if x > ARENA.x1 then x = ARENA.x1 end
		if y < ARENA.y0 then y = ARENA.y0 end
		if y > ARENA.y1 then y = ARENA.y1 end
		table.insert(out, {x = x, y = y, z = ARENA.z})
	end
	return out
end

function waveSpawn(waveIndex)
	local def = WAVES[waveIndex]
	if not def then
		return false
	end
	local name = def[1]
	local amount = def[2]
	local spots = waveSpawnOffsets(amount)
	local ok = 0
	for i = 1, amount do
		local summoned = doSummonCreature(name, spots[i])
		if summoned ~= 0 then
			ok = ok + 1
		end
	end
	return ok > 0
end

function waveStartOrNext(cid)
	if not wavePlayerInArena(cid) then
		doPlayerSendCancel(cid, "Entra a la Wave Arena primero (TP del templo).")
		return
	end

	local monsters = waveCountMonsters(cid)
	if monsters > 0 then
		doPlayerSendCancel(cid, "Quedan " .. monsters .. " monstruo(s). Mata a todos primero.")
		return
	end

	-- Si el dueno anterior se fue, reiniciar corrida al estar vacia.
	if WaveArenaState.wave > 0 and WaveArenaState.owner ~= 0 and WaveArenaState.owner ~= cid then
		if not wavePlayerInArena(WaveArenaState.owner) then
			WaveArenaState.wave = 0
			WaveArenaState.owner = 0
			WaveArenaState.ownerName = ""
		else
			doPlayerSendCancel(cid, "Corrida activa de " .. WaveArenaState.ownerName .. ".")
			return
		end
	end

	local nextWave = WaveArenaState.wave + 1
	if nextWave > table.getn(WAVES) then
		doPlayerSendTextMessage(cid, 22, "Completaste las " .. table.getn(WAVES) .. " oleadas. Ranking actualizado.")
		waveUpdateBest(cid, table.getn(WAVES))
		WaveArenaState.wave = 0
		WaveArenaState.owner = 0
		WaveArenaState.ownerName = ""
		doPlayerSendTextMessage(cid, 22, "Usa la palanca otra vez para reiniciar.")
		return
	end

	if not waveSpawn(nextWave) then
		doPlayerSendCancel(cid, "No se pudieron invocar monstruos. Avisa a un GM.")
		return
	end

	WaveArenaState.wave = nextWave
	WaveArenaState.owner = cid
	WaveArenaState.ownerName = getPlayerName(cid)
	waveUpdateBest(cid, nextWave)

	local def = WAVES[nextWave]
	doPlayerSendTextMessage(
		cid,
		22,
		"Oleada " .. nextWave .. "/" .. table.getn(WAVES) .. ": " .. def[2] .. "x " .. def[1]
	)
	doSendMagicEffect(getPlayerPosition(cid), 12)
end

function onUse(cid, item, frompos, item2, topos)
	if item.uid == UID_RANK then
		waveRankMessage(cid)
		return 1
	end
	if item.uid == UID_START then
		waveStartOrNext(cid)
		return 1
	end
	return 0
end
