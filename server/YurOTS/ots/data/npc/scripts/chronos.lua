-- Chronos — Reloj de Arena: sala compartida de oleadas que suben de nivel.
--
-- Ciclo fijo, igual para todos (reloj de pared, os.time()):
--   descanso de REST_SEC (sala vacía) -> oleadas 1..6 de WAVE_SEC cada una, cada una más fuerte -> otra vez.
-- Al empezar una oleada se van los monstruos que quedaron de la anterior y aparece la nueva.
-- Cada think (~1 s) los jugadores de la sala ven abajo: "Oleada 3 de 6: Orcos | quedan 42 s | despues: Acero",
-- y los braseros del norte echan fuego según la oleada (1 a 6).
-- Los textos que ve el jugador van sin tildes ni rayas: el cliente 7.6 no muestra UTF-8.
-- Requiere bindings NPC YUR_NPC_EXT: doSummonCreature, doRemoveCreature, doSendMagicEffect,
-- getTopCreature, isMonster.

-- Sala (debe coincidir con scripts/map/generate-sand-clock.py)
ROOM = {x0 = 333, y0 = 388, x1 = 343, y1 = 396, z = 6}
REST_SEC = 30
WAVE_SEC = 60

-- Oleadas en orden de dificultad. Pocos monstruos: la sala es chica (11x9).
WAVES = {
	{name = "Escarabajos", mobs = {{"Angry Scarab", 3}}},
	{name = "Cazadoras", mobs = {{"Angry Amazon", 2}, {"Furious Valkyrie", 1}}},
	{name = "Orcos", mobs = {{"Angry Orc Berserker", 2}, {"Angry Orc Shaman", 1}, {"Furious Orc Leader", 1}}},
	{name = "Acero", mobs = {{"Angry Hero", 1}, {"Angry Black Knight", 1}, {"Angry Gargoyle", 1}}},
	{name = "Necropolis", mobs = {{"Angry Vampire", 2}, {"Furious Necromancer", 1}, {"Angry Lich", 1}}},
	{name = "Abismo", mobs = {{"Angry Demon", 1}, {"Fury", 1}}},
}

-- Braseros del norte: el de la oleada N y los anteriores echan fuego.
BRAZIERS = {
	{x = 333, y = 388, z = 6}, {x = 334, y = 388, z = 6}, {x = 335, y = 388, z = 6},
	{x = 341, y = 388, z = 6}, {x = 342, y = 388, z = 6}, {x = 343, y = 388, z = 6},
}

SPAWN_SPOTS = {
	{x = 334, y = 390, z = 6}, {x = 338, y = 390, z = 6}, {x = 342, y = 390, z = 6},
	{x = 336, y = 391, z = 6}, {x = 340, y = 391, z = 6}, {x = 334, y = 393, z = 6},
	{x = 342, y = 393, z = 6}, {x = 337, y = 392, z = 6}, {x = 339, y = 392, z = 6},
	{x = 336, y = 393, z = 6}, {x = 340, y = 393, z = 6},
}

-- Efectos 7.6
FX_PUFF = 2
FX_RINGS = 7
FX_ENERGY = 10
FX_POP = 11
FX_FLAME = 15
FX_CLOUD = 20

MSG_SMALLINFO = 23 -- 0x17: línea de abajo, como el timer de trainers
MSG_RED_INFO = 18  -- 0x12: aviso en rojo (entrada, cambio de oleada)

current_wave = -1   -- -1 = todavía no se aplicó nada; 0 = descanso
room_players = {}

function sandClockInRoom(x, y, z)
	return z == ROOM.z and x >= ROOM.x0 and x <= ROOM.x1 and y >= ROOM.y0 and y <= ROOM.y1
end

-- Estado del ciclo: oleada (0 = descanso) y segundos que le quedan.
function sandClockState()
	local n = table.getn(WAVES)
	local t = math.fmod(os.time(), REST_SEC + n * WAVE_SEC)
	if t < REST_SEC then
		return 0, REST_SEC - t
	end
	t = t - REST_SEC
	return math.floor(t / WAVE_SEC) + 1, WAVE_SEC - math.fmod(t, WAVE_SEC)
end

function sandClockFormat(sec)
	if sec < 0 then
		sec = 0
	end
	local min = math.floor(sec / 60)
	local s = math.fmod(sec, 60)
	if min > 0 then
		return min .. " min " .. s .. " s"
	end
	return s .. " s"
end

-- Texto del estado actual, para la línea de abajo y para Chronos.
function sandClockStatus()
	local wave, remain = sandClockState()
	local n = table.getn(WAVES)
	if wave == 0 then
		return 'Descanso | la oleada 1 (' .. WAVES[1].name .. ') empieza en ' .. sandClockFormat(remain)
	end
	local text = 'Oleada ' .. wave .. ' de ' .. n .. ': ' .. WAVES[wave].name .. ' | quedan ' .. sandClockFormat(remain)
	if wave < n then
		return text .. ' | despues: ' .. WAVES[wave + 1].name
	end
	return text .. ' | despues: descanso'
end

RULES = 'Reloj de Arena: descanso de ' .. REST_SEC .. ' s y despues ' .. table.getn(WAVES) .. ' oleadas de '
	.. WAVE_SEC .. ' s, cada una mas fuerte. Los braseros marcan la oleada. Entra en el descanso para empezar desde la 1.'

function sandClockIsPlayerCid(cid)
	if cid == nil or cid == 0 or isMonster(cid) then
		return false
	end
	local name = creatureGetName(cid)
	return name ~= nil and name ~= '' and name ~= 'Chronos'
end

function sandClockTrackPlayer(cid)
	if not sandClockIsPlayerCid(cid) then
		return
	end
	local x, y, z = creatureGetPosition(cid)
	if x ~= nil and sandClockInRoom(x, y, z) then
		if not room_players[cid] then
			doPlayerSendTextMessage(cid, MSG_RED_INFO, RULES)
			doPlayerSendTextMessage(cid, MSG_RED_INFO, 'Ahora: ' .. sandClockStatus() .. '.')
		end
		room_players[cid] = true
	else
		room_players[cid] = nil
	end
end

function sandClockScanRoomPlayers()
	local seen = {}
	for x = ROOM.x0, ROOM.x1 do
		for y = ROOM.y0, ROOM.y1 do
			local cid = getTopCreature({x = x, y = y, z = ROOM.z})
			if sandClockIsPlayerCid(cid) then
				seen[cid] = true
				sandClockTrackPlayer(cid)
			end
		end
	end
	for old, _ in pairs(room_players) do
		if not seen[old] then
			room_players[old] = nil
		end
	end
end

function sandClockBroadcast(msgClass, text)
	for cid, _ in pairs(room_players) do
		local x, y, z = creatureGetPosition(cid)
		if x ~= nil and sandClockInRoom(x, y, z) and sandClockIsPlayerCid(cid) then
			doPlayerSendTextMessage(cid, msgClass, text)
		else
			room_players[cid] = nil
		end
	end
end

function sandClockClearMonsters()
	local toRemove = {}
	for x = ROOM.x0, ROOM.x1 do
		for y = ROOM.y0, ROOM.y1 do
			local cid = getTopCreature({x = x, y = y, z = ROOM.z})
			if cid ~= 0 and isMonster(cid) then
				table.insert(toRemove, cid)
			end
		end
	end
	for i = 1, table.getn(toRemove) do
		doRemoveCreature(toRemove[i])
	end
end

function sandClockSpawnWave(wave)
	local spot = 1
	for i = 1, table.getn(wave.mobs) do
		local name = wave.mobs[i][1]
		for n = 1, wave.mobs[i][2] do
			local pos = SPAWN_SPOTS[math.fmod(spot - 1, table.getn(SPAWN_SPOTS)) + 1]
			spot = spot + 1
			doSendMagicEffect(pos, FX_CLOUD)
			doSendMagicEffect(pos, FX_RINGS)
			if doSummonCreature(name, pos) ~= 0 then
				doSendMagicEffect(pos, FX_POP)
				doSendMagicEffect(pos, FX_ENERGY)
			else
				doSendMagicEffect(pos, FX_PUFF)
			end
		end
	end
end

function sandClockApply(wave, announce)
	sandClockClearMonsters()
	current_wave = wave
	if wave == 0 then
		if announce then
			selfSay('Descanso. La arena vuelve a empezar.')
			sandClockBroadcast(MSG_RED_INFO, 'Reloj de Arena: ronda terminada. Descanso de ' .. REST_SEC
				.. ' s; despues vuelve la oleada 1.')
		end
		return
	end
	sandClockSpawnWave(WAVES[wave])
	if announce then
		selfSay('Oleada ' .. wave .. ': ' .. WAVES[wave].name .. '!')
		sandClockBroadcast(MSG_RED_INFO, 'Reloj de Arena: oleada ' .. wave .. ' de ' .. table.getn(WAVES) .. ': '
			.. WAVES[wave].name .. '.')
	end
end

function sandClockEnsure()
	local wave = sandClockState()
	if current_wave == -1 then
		sandClockApply(wave, false)
	elseif wave ~= current_wave then
		sandClockApply(wave, true)
	end
end

-- Braseros encendidos: uno por oleada ya empezada (en el descanso, apagados). Solo si hay alguien mirando.
function sandClockShowProgress()
	if next(room_players) == nil then
		return
	end
	for i = 1, current_wave do
		if BRAZIERS[i] then
			doSendMagicEffect(BRAZIERS[i], FX_FLAME)
		end
	end
end

local function chronosDisappear(cid, pos)
	room_players[cid] = nil
	npcOnCreatureDisappear(cid)
end

local function onMessage(cid, msg)
	if npcIsHelp(msg) or msgcontains(msg, 'reglas') or msgcontains(msg, 'rules') then
		selfSay(RULES)
	elseif msgcontains(msg, 'time') or msgcontains(msg, 'tiempo') or msgcontains(msg, 'fase')
		or msgcontains(msg, 'phase') or msgcontains(msg, 'oleada') or msgcontains(msg, 'wave')
		or msgcontains(msg, 'reloj') then
		selfSay(sandClockStatus() .. '.')
	end
end

-- Cada think (~1 s): quién está en la sala, oleada que toca, línea de estado y braseros.
local function chronosThink()
	sandClockScanRoomPlayers()
	sandClockEnsure()
	sandClockBroadcast(MSG_SMALLINFO, 'Reloj de Arena | ' .. sandClockStatus())
	sandClockShowProgress()
	npcOnThink(45, '...')
end

npcDefine{
	greet = function(cid)
		return 'Hola ' .. creatureGetName(cid) .. '! Cuido el reloj. ' .. sandClockStatus()
			.. '. Di "reglas" u "oleada".'
	end,
	busy = 'Un momento...',
	onMessage = onMessage,
	onAppear = sandClockTrackPlayer,
	onDisappear = chronosDisappear,
	onThink = chronosThink,
}
