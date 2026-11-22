-- Chronos — Sand Clock v2: dynamic time-attack challenge (6 escalating waves). Pure ASCII (7.6 client).
--
-- State machine:
--   * IDLE: room empty and clean (never spawns monsters with nobody inside).
--   * PREP (15 s): countdown when the first player enters.
--   * ACTIVE (waves 1..6): starts with INITIAL_SAND (90 s), counts down 1 s per tick.
--     - Clearing all wave enemies (ignoring player summons) adds that wave's sand bonus and
--       moves quickly (BETWEEN = 5 s, sand paused) to the next wave.
--     - Clearing wave 6 before sand runs out -> VICTORY: personal best time + daily reward
--       (10000 gp, 40000 exp, 2 small gems; requires participating in >= 3 cleared waves).
--     - Running out of sand -> defeat, cleans round monsters, enters COOLDOWN (15 s).
--   * If everyone leaves mid-round, resets to IDLE after EMPTY_RESET_SEC (3 s).

-- Room (must match scripts/map/generate-sand-clock.py)
ROOM = {x0 = 600, y0 = 320, x1 = 610, y1 = 328, z = 6}

PREP_SEC = 15
BETWEEN_SEC = 5
WIN_COOLDOWN_SEC = 20
FAIL_COOLDOWN_SEC = 15
EMPTY_RESET_SEC = 3

INITIAL_SAND = 90
MIN_WAVES_FOR_REWARD = 3

-- Sand Clock storage keys (9400-9402)
STORAGE_SC_REWARD_DAY = 9400   -- YYYYMMDD of last daily reward claimed
STORAGE_SC_BEST_TIME = 9401    -- fastest combat time (seconds) across all 6 waves
STORAGE_SC_CLEARS = 9402       -- total victories

-- Daily completion reward
REWARD_GOLD = 10000
REWARD_EXP = 40000
REWARD_GEM_COUNT = 2
SMALL_GEMS = {
	{2145, "small diamonds"},
	{2146, "small sapphires"},
	{2147, "small rubies"},
	{2149, "small emeralds"},
	{2150, "small amethysts"},
}

-- 6 strictly escalating waves (normal monsters, no rage variants).
WAVES = {
	{name = "Dunes",         bonus = 40, mobs = {{"Scarab", 2}, {"Mummy", 2}}},
	{name = "Horde",         bonus = 45, mobs = {{"Orc Berserker", 2}, {"Orc Shaman", 1}, {"Orc Leader", 1}, {"Orc Warlord", 1}}},
	{name = "Scarabs",       bonus = 50, mobs = {{"Ancient Scarab", 2}, {"Scarab", 2}}},
	{name = "Necropolis",    bonus = 55, mobs = {{"Vampire", 2}, {"Necromancer", 1}, {"Lich", 1}, {"Vampire Bride", 1}}},
	{name = "Steel",         bonus = 65, mobs = {{"Hero", 1}, {"Black Knight", 1}, {"Dragon Lord", 1}}},
	{name = "Time Guardian", bonus = 0,  mobs = {{"Demon", 1}}},
}

BOSS_SUMMON_NAMES = {
	["Snake"] = true,
	["Skeleton"] = true,
	["Ghoul"] = true,
	["Mummy"] = true,
	["Fire Elemental"] = true,
}

BRAZIERS = {
	{x = 600, y = 320, z = 6}, {x = 601, y = 320, z = 6}, {x = 602, y = 320, z = 6},
	{x = 608, y = 320, z = 6}, {x = 609, y = 320, z = 6}, {x = 610, y = 320, z = 6},
}

SPAWN_SPOTS = {
	{x = 601, y = 322, z = 6}, {x = 605, y = 322, z = 6}, {x = 609, y = 322, z = 6},
	{x = 603, y = 323, z = 6}, {x = 607, y = 323, z = 6}, {x = 601, y = 325, z = 6},
	{x = 609, y = 325, z = 6}, {x = 604, y = 324, z = 6}, {x = 606, y = 324, z = 6},
	{x = 603, y = 325, z = 6}, {x = 607, y = 325, z = 6},
}

FX_PUFF = 2
FX_RINGS = 7
FX_ENERGY = 10
FX_POP = 11
FX_FLAME = 15
FX_CLOUD = 20

MSG_SMALLINFO = 23
MSG_RED_INFO = 18

sc_state = "IDLE"
sc_wave = 0
sc_timer = 0
sc_sand = 0
sc_elapsed = 0
sc_empty_ticks = 0
sc_wave_spawned = 0
sc_last_result = ""

room_players = {}
wave_mobs = {}
pre_wave_mobs = {}
waves_seen = {}

RULES = 'Sand Clock: 6-wave time attack. You start with ' .. INITIAL_SAND
	.. ' s of sand; each cleared wave adds bonus time and advances in ' .. BETWEEN_SEC
	.. ' s. Clear all 6 waves to claim Chronos daily reward (min '
	.. MIN_WAVES_FOR_REWARD .. ' waves participated).'

REWARD_INFO = 'Chronos daily reward (once per day for clearing all 6 waves): '
	.. REWARD_GOLD .. ' gp, ' .. REWARD_EXP .. ' exp, and ' .. REWARD_GEM_COUNT
	.. ' small gems. I also track your personal best time.'

function sandClockInRoom(x, y, z)
	return z == ROOM.z and x >= ROOM.x0 and x <= ROOM.x1 and y >= ROOM.y0 and y <= ROOM.y1
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

local function todayId()
	return tonumber(os.date("%Y%m%d")) or 0
end

local function storageVal(cid, key)
	local v = getPlayerStorageValue(cid, key)
	if v == nil or v < 0 then
		return 0
	end
	return v
end

local function isRageName(name)
	if not name then
		return false
	end
	return string.sub(name, 1, 6) == "Angry "
		or string.sub(name, 1, 8) == "Furious "
		or string.sub(name, 1, 8) == "Enraged "
end

function sandClockIsPlayerCid(cid)
	if cid == nil or cid == 0 or isMonster(cid) then
		return false
	end
	local name = creatureGetName(cid)
	return name ~= nil and name ~= '' and name ~= 'Chronos'
end

local function scanRoomMonsters()
	local list = {}
	for x = ROOM.x0, ROOM.x1 do
		for y = ROOM.y0, ROOM.y1 do
			local pos = {x = x, y = y, z = ROOM.z}
			local cid = getTopCreature(pos)
			if cid ~= 0 and isMonster(cid) then
				table.insert(list, {cid = cid, pos = pos, name = creatureGetName(cid)})
			end
		end
	end
	return list
end

local function countWaveEnemies(monsters)
	local n = 0
	for i = 1, table.getn(monsters) do
		local m = monsters[i]
		if wave_mobs[m.cid] or isRageName(m.name) then
			n = n + 1
		end
	end
	return n
end

function sandClockClearMonsters(allMonsters)
	local monsters = scanRoomMonsters()
	for i = 1, table.getn(monsters) do
		local m = monsters[i]
		local remove = allMonsters
			or wave_mobs[m.cid]
			or isRageName(m.name)
			or (BOSS_SUMMON_NAMES[m.name] and not pre_wave_mobs[m.cid])
		if remove then
			doSendMagicEffect(m.pos, FX_PUFF)
			doRemoveCreature(m.cid)
		end
	end
	wave_mobs = {}
end

function sandClockStatus(enemyCount)
	local n = table.getn(WAVES)
	if sc_state == "IDLE" then
		return 'Idle | enter the room to start the ' .. n .. '-wave time attack'
	elseif sc_state == "PREP" then
		return 'Get ready | wave 1 (' .. WAVES[1].name .. ') in ' .. sandClockFormat(sc_timer)
			.. ' | starting sand: ' .. sandClockFormat(INITIAL_SAND)
	elseif sc_state == "ACTIVE" then
		local countPart = ''
		if enemyCount ~= nil then
			countPart = ' | ' .. enemyCount .. ' left'
		end
		return 'Wave ' .. sc_wave .. '/' .. n .. ': ' .. WAVES[sc_wave].name
			.. countPart .. ' | Sand: ' .. sandClockFormat(sc_sand)
	elseif sc_state == "BETWEEN" then
		local nextName = WAVES[sc_wave + 1] and WAVES[sc_wave + 1].name or ''
		return 'Wave ' .. sc_wave .. ' cleared! Next (' .. nextName .. ') in ' .. sandClockFormat(sc_timer)
			.. ' | Sand: ' .. sandClockFormat(sc_sand)
	elseif sc_state == "COOLDOWN" then
		local label = 'Rest'
		if sc_last_result == 'win' then
			label = 'Victory! Rest'
		elseif sc_last_result == 'fail' then
			label = 'Time up | rest'
		end
		return label .. ' | next round in ' .. sandClockFormat(sc_timer)
	end
	return 'Idle'
end

function sandClockTrackPlayer(cid)
	if not sandClockIsPlayerCid(cid) then
		return
	end
	local x, y, z = creatureGetPosition(cid)
	if x ~= nil and sandClockInRoom(x, y, z) then
		if not room_players[cid] then
			doPlayerSendTextMessage(cid, MSG_RED_INFO, RULES)
			doPlayerSendTextMessage(cid, MSG_RED_INFO, 'Now: ' .. sandClockStatus() .. '.')
		end
		room_players[cid] = true
	else
		room_players[cid] = nil
	end
end

function sandClockScanRoomPlayers()
	local seen = {}
	local count = 0
	for x = ROOM.x0, ROOM.x1 do
		for y = ROOM.y0, ROOM.y1 do
			local cid = getTopCreature({x = x, y = y, z = ROOM.z})
			if sandClockIsPlayerCid(cid) then
				if not seen[cid] then
					seen[cid] = true
					count = count + 1
					sandClockTrackPlayer(cid)
				end
			end
		end
	end
	for old, _ in pairs(room_players) do
		if not seen[old] then
			room_players[old] = nil
		end
	end
	return count
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

local function snapshotPreWaveMobs()
	pre_wave_mobs = {}
	local monsters = scanRoomMonsters()
	for i = 1, table.getn(monsters) do
		pre_wave_mobs[monsters[i].cid] = true
	end
end

function sandClockSpawnWave(wave)
	snapshotPreWaveMobs()
	wave_mobs = {}
	local spot = 1
	local spawned = 0
	for i = 1, table.getn(wave.mobs) do
		local name = wave.mobs[i][1]
		for _ = 1, wave.mobs[i][2] do
			local pos = SPAWN_SPOTS[math.fmod(spot - 1, table.getn(SPAWN_SPOTS)) + 1]
			spot = spot + 1
			doSendMagicEffect(pos, FX_CLOUD)
			doSendMagicEffect(pos, FX_RINGS)
			local mid = doSummonCreature(name, pos)
			if mid ~= 0 then
				wave_mobs[mid] = true
				spawned = spawned + 1
				doSendMagicEffect(pos, FX_POP)
				doSendMagicEffect(pos, FX_ENERGY)
			else
				doSendMagicEffect(pos, FX_PUFF)
			end
		end
	end
	return spawned
end

local function resetToIdle()
	sandClockClearMonsters(true)
	sc_state = "IDLE"
	sc_wave = 0
	sc_timer = 0
	sc_sand = 0
	sc_elapsed = 0
	sc_empty_ticks = 0
	sc_wave_spawned = 0
	sc_last_result = ""
	pre_wave_mobs = {}
	waves_seen = {}
end

local function startWave(waveIdx)
	sc_state = "ACTIVE"
	sc_wave = waveIdx
	sc_timer = 0
	sc_wave_spawned = sandClockSpawnWave(WAVES[waveIdx])
	local n = table.getn(WAVES)
	selfSay('Wave ' .. waveIdx .. ': ' .. WAVES[waveIdx].name .. '!')
	sandClockBroadcast(MSG_RED_INFO, 'Sand Clock: wave ' .. waveIdx .. '/' .. n .. ': '
		.. WAVES[waveIdx].name .. ' | Sand left: ' .. sandClockFormat(sc_sand) .. '.')
end

local function startNewRound()
	sc_sand = INITIAL_SAND
	sc_elapsed = 0
	sc_empty_ticks = 0
	sc_last_result = ""
	waves_seen = {}
	startWave(1)
end

local function awardVictory()
	local totalSec = math.max(1, sc_elapsed)
	local today = todayId()
	local gemIdx = math.random(1, table.getn(SMALL_GEMS))
	local gem = SMALL_GEMS[gemIdx]

	for i = 1, table.getn(BRAZIERS) do
		doSendMagicEffect(BRAZIERS[i], FX_ENERGY)
		doSendMagicEffect(BRAZIERS[i], FX_FLAME)
	end
	selfSay('Victory! You beat the Sand Clock in ' .. sandClockFormat(totalSec) .. '!')
	sandClockBroadcast(MSG_RED_INFO, 'Sand Clock CLEARED in ' .. sandClockFormat(totalSec)
		.. ' (' .. sandClockFormat(sc_sand) .. ' of sand to spare)!')

	for cid, _ in pairs(room_players) do
		local x, y, z = creatureGetPosition(cid)
		if x ~= nil and sandClockInRoom(x, y, z) and sandClockIsPlayerCid(cid) then
			local pname = string.lower(creatureGetName(cid) or '')
			local seenCount = waves_seen[pname] or 0
			local clears = storageVal(cid, STORAGE_SC_CLEARS) + 1
			setPlayerStorageValue(cid, STORAGE_SC_CLEARS, clears)

			local prevBest = storageVal(cid, STORAGE_SC_BEST_TIME)
			if prevBest == 0 or totalSec < prevBest then
				setPlayerStorageValue(cid, STORAGE_SC_BEST_TIME, totalSec)
				doPlayerSendTextMessage(cid, MSG_RED_INFO,
					'New personal best in Sand Clock: ' .. sandClockFormat(totalSec) .. '!')
			end

			if seenCount < MIN_WAVES_FOR_REWARD then
				doPlayerSendTextMessage(cid, MSG_RED_INFO,
					'You participated in ' .. seenCount .. '/' .. MIN_WAVES_FOR_REWARD
					.. ' minimum waves required for Chronos daily reward.')
			elseif storageVal(cid, STORAGE_SC_REWARD_DAY) == today then
				doPlayerSendTextMessage(cid, MSG_RED_INFO,
					'You already claimed Chronos daily reward today. Come back tomorrow!')
			else
				setPlayerStorageValue(cid, STORAGE_SC_REWARD_DAY, today)
				doPlayerAddMoney(cid, REWARD_GOLD)
				doPlayerAddExp(cid, REWARD_EXP)
				doPlayerAddItem(cid, gem[1], REWARD_GEM_COUNT)
				doPlayerSendTextMessage(cid, MSG_RED_INFO,
					'Chronos daily reward: ' .. REWARD_GOLD .. ' gp, ' .. REWARD_EXP
					.. ' exp, and ' .. REWARD_GEM_COUNT .. ' ' .. gem[2] .. '!')
			end
		end
	end
end

function sandClockShowProgress()
	if next(room_players) == nil then
		return
	end
	if sc_state ~= "ACTIVE" and sc_state ~= "BETWEEN" then
		return
	end
	for i = 1, sc_wave do
		if BRAZIERS[i] then
			doSendMagicEffect(BRAZIERS[i], FX_FLAME)
		end
	end
end

local function recordWaveParticipation()
	for cid, _ in pairs(room_players) do
		local x, y, z = creatureGetPosition(cid)
		if x ~= nil and sandClockInRoom(x, y, z) and sandClockIsPlayerCid(cid) then
			local pname = string.lower(creatureGetName(cid) or '')
			if pname ~= '' then
				waves_seen[pname] = (waves_seen[pname] or 0) + 1
			end
		end
	end
end

local function personalRecordText(cid)
	local best = storageVal(cid, STORAGE_SC_BEST_TIME)
	local clears = storageVal(cid, STORAGE_SC_CLEARS)
	local claimed = storageVal(cid, STORAGE_SC_REWARD_DAY) == todayId()
	local bestStr = 'no clear yet'
	if best > 0 then
		bestStr = sandClockFormat(best) .. ' (' .. clears .. ' clear(s))'
	end
	local dailyStr = 'available today'
	if claimed then
		dailyStr = 'already claimed today'
	end
	return 'Your Sand Clock record: ' .. bestStr .. '. Daily reward: ' .. dailyStr .. '.'
end

local function chronosDisappear(cid, pos)
	room_players[cid] = nil
	npcOnCreatureDisappear(cid)
end

local function onMessage(cid, msg)
	if npcIsHelp(msg) or msgcontains(msg, 'reglas') or msgcontains(msg, 'rules') then
		selfSay(RULES)
	elseif msgcontains(msg, 'premio') or msgcontains(msg, 'premios')
		or msgcontains(msg, 'reward') or msgcontains(msg, 'rewards')
		or msgcontains(msg, 'recompensa') or msgcontains(msg, 'recompensas') then
		selfSay(REWARD_INFO)
	elseif msgcontains(msg, 'record') or msgcontains(msg, 'records')
		or msgcontains(msg, 'marca') or msgcontains(msg, 'marcas') or msgcontains(msg, 'best') then
		selfSay(personalRecordText(cid))
	elseif msgcontains(msg, 'time') or msgcontains(msg, 'tiempo') or msgcontains(msg, 'fase')
		or msgcontains(msg, 'phase') or msgcontains(msg, 'oleada') or msgcontains(msg, 'oleadas')
		or msgcontains(msg, 'wave') or msgcontains(msg, 'waves')
		or msgcontains(msg, 'reloj') or msgcontains(msg, 'estado') or msgcontains(msg, 'status') then
		selfSay(sandClockStatus() .. '.')
	end
end

local function chronosThink()
	local pCount = sandClockScanRoomPlayers()
	local enemyCount = nil

	if pCount == 0 then
		if sc_state == "PREP" or sc_state == "COOLDOWN" then
			resetToIdle()
		elseif sc_state == "ACTIVE" or sc_state == "BETWEEN" then
			sc_empty_ticks = sc_empty_ticks + 1
			if sc_empty_ticks >= EMPTY_RESET_SEC then
				resetToIdle()
			end
		end
		npcOnThink(45, '...')
		return
	end

	sc_empty_ticks = 0

	if sc_state == "IDLE" then
		sc_state = "PREP"
		sc_timer = PREP_SEC
		selfSay('The hourglass awakens! Round starts in ' .. PREP_SEC .. ' seconds.')
		sandClockBroadcast(MSG_RED_INFO, 'Sand Clock: get ready! Wave 1 (' .. WAVES[1].name
			.. ') starts in ' .. PREP_SEC .. ' s.')
	elseif sc_state == "PREP" then
		sc_timer = sc_timer - 1
		if sc_timer == 5 then
			selfSay('5 seconds! Get ready!')
		end
		if sc_timer <= 0 then
			startNewRound()
			enemyCount = sc_wave_spawned
		end
	elseif sc_state == "ACTIVE" then
		local monsters = scanRoomMonsters()
		enemyCount = countWaveEnemies(monsters)

		if sc_wave_spawned > 0 and enemyCount == 0 then
			recordWaveParticipation()
			sandClockClearMonsters(false)
			local n = table.getn(WAVES)
			if sc_wave >= n then
				awardVictory()
				sc_state = "COOLDOWN"
				sc_timer = WIN_COOLDOWN_SEC
				sc_last_result = "win"
				sc_wave = 0
			else
				local bonus = WAVES[sc_wave].bonus
				sc_sand = sc_sand + bonus
				local nextW = WAVES[sc_wave + 1]
				selfSay('Wave ' .. sc_wave .. ' cleared! +' .. bonus .. ' s of sand!')
				sandClockBroadcast(MSG_RED_INFO, 'Wave ' .. sc_wave .. '/' .. n .. ' (' .. WAVES[sc_wave].name
					.. ') cleared! +' .. bonus .. ' s of sand (' .. sandClockFormat(sc_sand)
					.. ' left). Next in ' .. BETWEEN_SEC .. ' s: ' .. nextW.name .. '.')
				sc_state = "BETWEEN"
				sc_timer = BETWEEN_SEC
			end
			enemyCount = nil
		else
			sc_sand = sc_sand - 1
			sc_elapsed = sc_elapsed + 1
			if sc_sand == 15 then
				selfSay('15 seconds of sand left! Hurry!')
			elseif sc_sand == 5 then
				selfSay('5 seconds of sand left!')
			end
			if sc_sand <= 0 then
				sandClockClearMonsters(false)
				local n = table.getn(WAVES)
				selfSay('The sand ran out! Round over.')
				sandClockBroadcast(MSG_RED_INFO, 'Sand Clock: out of sand on wave '
					.. sc_wave .. '/' .. n .. '! Rest for ' .. FAIL_COOLDOWN_SEC .. ' s.')
				sc_state = "COOLDOWN"
				sc_timer = FAIL_COOLDOWN_SEC
				sc_last_result = "fail"
				sc_wave = 0
				enemyCount = nil
			end
		end
	elseif sc_state == "BETWEEN" then
		sc_timer = sc_timer - 1
		if sc_timer <= 0 then
			startWave(sc_wave + 1)
			enemyCount = sc_wave_spawned
		end
	elseif sc_state == "COOLDOWN" then
		sc_timer = sc_timer - 1
		if sc_timer == 5 then
			selfSay('5 seconds until a new round!')
		end
		if sc_timer <= 0 then
			startNewRound()
			enemyCount = sc_wave_spawned
		end
	end

	sandClockBroadcast(MSG_SMALLINFO, 'Sand Clock | ' .. sandClockStatus(enemyCount))
	sandClockShowProgress()
	npcOnThink(45, '...')
end

npcDefine{
	greet = function(cid)
		return 'Hello ' .. creatureGetName(cid) .. '! I keep the Sand Clock. ' .. sandClockStatus()
			.. '. Say "rules", "rewards", "record", or "status".'
	end,
	busy = 'One moment...',
	onMessage = onMessage,
	onAppear = sandClockTrackPlayer,
	onDisappear = chronosDisappear,
	onThink = chronosThink,
}
