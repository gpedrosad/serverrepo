-- Wave Arena v3 "Jungle Clearing". See docs/gameplay/WAVE_ARENA.md. Pure ASCII (7.6 client).
--
-- Levers:
--   7100 camp: teleport group (puller + 3x2 pad players) and start wave 1.
--   7101 camp: weekly ranking (cleared wave + fastest time) + personal best + clearing status.
--   7102 clearing: next wave. Requires cleared room; records cleared wave + time for all inside.
--   7103 clearing: retire to camp keeping the last cleared wave.
--
-- Rules:
--   * One run at a time; occupied while any player is inside.
--   * Orphan monsters left behind are cleared in ~2 s by Kaelen (camp NPC); start() waits for clean room.
--   * Score tracks CLEARED waves; weekly ranking breaks ties by fastest run time.
--   * 20 progressive waves (lvl 25 to 100+), boss every 5; group scaling capped to fit spawns.
--   * Weekly rewards (coins + small gems) on first weekly clear of waves 5 / 10 / 15 / 20.

-- BEGIN LAYOUT (generado por scripts/map/generate-wave-arena.py)
ARENA = {x0 = 600, y0 = 205, x1 = 612, y1 = 215, z = 7}
CAMP = {x0 = 602, y0 = 220, x1 = 610, y1 = 224, z = 7}
PAD = {x0 = 605, y0 = 221, x1 = 607, y1 = 222, z = 7}
CAMP_LANDING = {x = 606, y = 223, z = 7}
-- ARRIVALS[1] = el que tira; la cantidad es el tope del grupo
ARRIVALS = {{x = 606, y = 214, z = 7}, {x = 605, y = 214, z = 7}, {x = 607, y = 214, z = 7}, {x = 606, y = 213, z = 7}, {x = 605, y = 213, z = 7}, {x = 607, y = 213, z = 7}, {x = 604, y = 214, z = 7}}
-- SPAWNS[1] = jefe; el resto en orden de reparto
SPAWNS = {{x = 606, y = 206, z = 7}, {x = 603, y = 205, z = 7}, {x = 609, y = 205, z = 7}, {x = 600, y = 208, z = 7}, {x = 612, y = 208, z = 7}, {x = 605, y = 205, z = 7}, {x = 607, y = 205, z = 7}, {x = 600, y = 210, z = 7}, {x = 612, y = 210, z = 7}, {x = 602, y = 206, z = 7}, {x = 610, y = 206, z = 7}, {x = 604, y = 207, z = 7}, {x = 608, y = 207, z = 7}, {x = 600, y = 212, z = 7}, {x = 612, y = 212, z = 7}, {x = 606, y = 208, z = 7}}
-- END LAYOUT

UID_START, UID_RANK, UID_NEXT, UID_RETIRE = 7100, 7101, 7102, 7103

STORAGE_WEEK = 9300            -- monotonic Monday-UTC week id
STORAGE_BEST_WEEK = 9301       -- best cleared wave this week
STORAGE_BEST_ALL = 9302        -- all-time best cleared wave
STORAGE_RUN_WAVE = 9303        -- active wave (reload fallback + read by Kaelen for HUD)
STORAGE_BEST_WEEK_TIME = 9304  -- fastest time (seconds) for STORAGE_BEST_WEEK
STORAGE_RUN_START = 9305       -- os.time() when current run started (reload fallback)
STORAGE_REWARD = 9310          -- 9310 + i - 1: week id when REWARDS[i] was claimed

RANK_FILE = "data/logs/wave_arena_rank.json"
MAX_RANK = 10
MAX_PACK_MOBS = 14             -- never exceed the 15 pack spots in SPAWNS[2..16]
MSG = 22                       -- MSG_INFO
EFFECT_TELEPORT, EFFECT_WAVE = 11, 12

-- Strictly escalating 20-wave lineup (1-player base, no rage variants):
--   1-5:   Jungle & Frontier (lvl 25-40)  | Boss 5:  Red Kongra
--   6-10:  Ruins & Swamp (lvl 40-65)      | Boss 10: Giant Spider
--   11-15: Beasts & Dragons (lvl 65-85)   | Boss 15: Behemoth
--   16-20: Abyss & Deep Jungle (85-110+)  | Boss 20: Old Widow
WAVES = {
	{pack = {{"Orc Warrior", 2}, {"Orc Spearman", 2}, {"Minotaur", 1}}},
	{pack = {{"Minotaur Guard", 2}, {"Minotaur Archer", 2}, {"Minotaur Mage", 1}}},
	{pack = {{"Tarantula", 3}, {"Terror Bird", 2}}},
	{pack = {{"Cyclops", 2}, {"Dwarf Guard", 2}, {"Cyclops Drone", 1}}},
	{boss = "Red Kongra", pack = {{"Kongra", 2}, {"Sibang", 2}}},
	{pack = {{"Lizard Templar", 2}, {"Lizard Sentinel", 2}, {"Lizard Snakecharmer", 1}}},
	{pack = {{"Vampire", 2}, {"Demon Skeleton", 2}, {"Necromancer", 1}}},
	{pack = {{"Ancient Scarab", 2}, {"Scarab", 2}}},
	{pack = {{"Dragon", 2}, {"Wyvern", 1}}},
	{boss = "Giant Spider", pack = {{"Crystal Spider", 1}, {"Tarantula", 2}}},
	{pack = {{"Hero", 1}, {"Black Knight", 1}, {"Undead Gladiator", 1}}},
	{pack = {{"Bog Raider", 2}, {"Mutated Tiger", 2}}},
	{pack = {{"Dragon Lord", 2}, {"Dragon", 1}}},
	{pack = {{"Hydra", 2}, {"Emerald Scarab", 1}}},
	{boss = "Behemoth", pack = {{"Dragon Lord", 2}}},
	{pack = {{"Frost Dragon", 2}, {"Ice Spider", 1}, {"Ice Monk", 1}}},
	{pack = {{"Black Dragon", 2}, {"Hellhound", 2}}},
	{pack = {{"Warlock", 2}, {"Lich", 1}, {"Banshee", 1}}},
	{pack = {{"Dark Hydra", 2}, {"Behemoth", 1}}},
	{boss = "Old Widow", pack = {{"Dark Hydra", 1}, {"Hydra", 1}}},
}

-- Weekly milestone rewards (once per week per player): coins + small gems.
REWARDS = {
	{wave = 5,  items = {{2152, 10}, {2149, 1}}, text = "10 platinum coins and 1 small emerald"},
	{wave = 10, items = {{2152, 30}, {2146, 2}}, text = "30 platinum coins and 2 small sapphires"},
	{wave = 15, items = {{2160, 1},  {2147, 3}}, text = "1 crystal coin and 3 small rubies"},
	{wave = 20, items = {{2160, 3},  {2145, 5}}, text = "3 crystal coins and 5 small diamonds"},
}

-- In-memory run state (mirrored in STORAGE_RUN_WAVE / STORAGE_RUN_START).
if not WaveRun then
	WaveRun = {wave = 0, startedAt = 0}
end

-------------------------------------------------------------------- helpers

-- Monotonic week starting Monday 00:00 UTC (never splits mid-week on Jan 1).
local function weekId()
	return math.floor((os.time() - 345600) / 604800)
end

local function formatDuration(sec)
	if not sec or sec <= 0 then
		return "--"
	end
	local m = math.floor(sec / 60)
	local s = math.fmod(sec, 60)
	if m > 0 then
		return m .. "m " .. s .. "s"
	end
	return s .. "s"
end

local function inBox(pos, box)
	return pos ~= nil and pos.z == box.z
		and pos.x >= box.x0 and pos.x <= box.x1
		and pos.y >= box.y0 and pos.y <= box.y1
end

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

-------------------------------------------------------------------- ranking

local function isBetterScore(wave, secs, prevWave, prevSecs)
	if wave ~= prevWave then
		return wave > prevWave
	end
	if secs <= 0 then
		return false
	end
	if prevSecs <= 0 then
		return true
	end
	return secs < prevSecs
end

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
	local hasV3 = false
	for name, w, t in string.gmatch(raw, '"([^"]+)"%s*:%s*%{%s*"wave"%s*:%s*(%d+)%s*,%s*"time"%s*:%s*(%d+)%s*%}') do
		data.scores[name] = {wave = tonumber(w), time = tonumber(t)}
		hasV3 = true
	end
	if not hasV3 then
		local block = string.match(raw, '"scores"%s*:%s*%{(.-)%}')
		if block then
			for name, score in string.gmatch(block, '"([^"]+)"%s*:%s*(%d+)') do
				data.scores[name] = {wave = tonumber(score), time = 0}
			end
		end
	end
	return data
end

local function rankSorted(data)
	local list = {}
	for n, s in pairs(data.scores) do
		table.insert(list, {name = n, wave = s.wave, time = s.time or 0})
	end
	table.sort(list, function(a, b)
		if a.wave ~= b.wave then
			return a.wave > b.wave
		end
		if a.time ~= b.time then
			if a.time <= 0 then return false end
			if b.time <= 0 then return true end
			return a.time < b.time
		end
		return a.name < b.name
	end)
	return list
end

local function rankSave(name, wave, elapsed)
	if not name or wave < 1 then
		return
	end
	local data = rankLoad()
	local prev = data.scores[name]
	if prev and not isBetterScore(wave, elapsed, prev.wave, prev.time or 0) then
		return
	end
	data.scores[name] = {wave = wave, time = elapsed}
	local list = rankSorted(data)
	local parts = {}
	for i = 1, math.min(MAX_RANK, table.getn(list)) do
		local e = list[i]
		table.insert(parts, '    "' .. e.name .. '": {"wave": ' .. e.wave .. ', "time": ' .. e.time .. '}')
	end
	local f = io.open(RANK_FILE, "w")
	if f then
		f:write('{\n  "week": ' .. data.week .. ',\n  "scores": {\n' .. table.concat(parts, ",\n") .. "\n  }\n}\n")
		f:close()
	end
end

-------------------------------------------------------------------- records & rewards

local function ensureWeek(uid)
	if storage(uid, STORAGE_WEEK) ~= weekId() then
		setPlayerStorageValue(uid, STORAGE_WEEK, weekId())
		setPlayerStorageValue(uid, STORAGE_BEST_WEEK, 0)
		setPlayerStorageValue(uid, STORAGE_BEST_WEEK_TIME, 0)
	end
end

local function record(uid, cleared, elapsed)
	if cleared < 1 then
		return
	end
	ensureWeek(uid)
	local prevWave = storage(uid, STORAGE_BEST_WEEK)
	local prevTime = storage(uid, STORAGE_BEST_WEEK_TIME)
	if isBetterScore(cleared, elapsed, prevWave, prevTime) then
		setPlayerStorageValue(uid, STORAGE_BEST_WEEK, cleared)
		setPlayerStorageValue(uid, STORAGE_BEST_WEEK_TIME, elapsed)
		rankSave(getPlayerName(uid), cleared, elapsed)
	end
	if cleared > storage(uid, STORAGE_BEST_ALL) then
		setPlayerStorageValue(uid, STORAGE_BEST_ALL, cleared)
	end
	for i, r in ipairs(REWARDS) do
		if cleared >= r.wave and storage(uid, STORAGE_REWARD + i - 1) ~= weekId() then
			setPlayerStorageValue(uid, STORAGE_REWARD + i - 1, weekId())
			for _, it in ipairs(r.items) do
				doPlayerAddItem(uid, it[1], it[2])
			end
			doPlayerSendTextMessage(uid, MSG, "Weekly reward for clearing wave " .. r.wave .. ": " .. r.text .. ".")
		end
	end
end

-------------------------------------------------------------------- waves

-- Group scaling: +30% per extra player, capped at MAX_PACK_MOBS to fit spawn spots.
local function scaledPack(w, players)
	local mult = 1 + 0.30 * math.max(0, players - 1)
	local counts = {}
	local total = 0
	for i, p in ipairs(w.pack) do
		local c = math.max(1, math.floor(p[2] * mult + 0.5))
		counts[i] = c
		total = total + c
	end
	while total > MAX_PACK_MOBS do
		local bestIdx, bestVal = 0, 1
		for i, c in ipairs(counts) do
			if c > bestVal then
				bestVal = c
				bestIdx = i
			end
		end
		if bestIdx == 0 then
			break
		end
		counts[bestIdx] = counts[bestIdx] - 1
		total = total - 1
	end
	return counts
end

local function describe(n, players)
	local w = WAVES[n]
	local counts = scaledPack(w, players)
	local parts = {}
	if w.boss then
		table.insert(parts, "BOSS " .. w.boss)
	end
	for i, p in ipairs(w.pack) do
		table.insert(parts, counts[i] .. " " .. p[1])
	end
	return "Wave " .. n .. "/" .. table.getn(WAVES) .. ": " .. table.concat(parts, " + ")
end

local function spawnWave(n, players)
	local w = WAVES[n]
	local counts = scaledPack(w, players)
	local ok, spot = 0, 2
	if w.boss and doSummonCreature(w.boss, SPAWNS[1]) ~= 0 then
		ok = ok + 1
	end
	for i, p in ipairs(w.pack) do
		for _ = 1, counts[i] do
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

local function setRunState(n, startedAt, players)
	WaveRun.wave = n
	WaveRun.startedAt = startedAt
	for _, uid in ipairs(players) do
		setPlayerStorageValue(uid, STORAGE_RUN_WAVE, n)
		setPlayerStorageValue(uid, STORAGE_RUN_START, startedAt)
	end
end

local function currentRun(players)
	if WaveRun.wave == 0 then
		for _, uid in ipairs(players) do
			WaveRun.wave = math.max(WaveRun.wave, storage(uid, STORAGE_RUN_WAVE))
		end
	end
	if WaveRun.startedAt == 0 then
		for _, uid in ipairs(players) do
			local st = storage(uid, STORAGE_RUN_START)
			if st > 0 and (WaveRun.startedAt == 0 or st < WaveRun.startedAt) then
				WaveRun.startedAt = st
			end
		end
	end
	local elapsed = 0
	if WaveRun.startedAt > 0 then
		elapsed = math.max(1, os.time() - WaveRun.startedAt)
	end
	return WaveRun.wave, elapsed
end

local function launch(n, startedAt, players)
	local got = spawnWave(n, table.getn(players))
	setRunState(n, startedAt, players)
	tellAll(players, describe(n, table.getn(players)) .. " (" .. got .. " summoned).")
	return got
end

-------------------------------------------------------------------- levers

local function start(cid)
	if not inBox(getPlayerPosition(cid), CAMP) then
		doPlayerSendCancel(cid, "Use the lever from the camp.")
		return
	end
	local inside = scan(ARENA)
	if table.getn(inside.players) > 0 then
		local w = currentRun(inside.players)
		doPlayerSendCancel(cid, "Run in progress by " .. names(inside.players) ..
			" (wave " .. w .. "/" .. table.getn(WAVES) .. ").")
		return
	end
	if inside.monsters > 0 then
		doPlayerSendCancel(cid, "The clearing is resetting from the previous run. Try again in 2 seconds.")
		return
	end

	local group, left = padGroup(cid, table.getn(ARRIVALS))
	for i, uid in ipairs(group) do
		doTeleportThing(uid, ARRIVALS[i])
	end
	doSendMagicEffect(ARRIVALS[1], EFFECT_TELEPORT)
	local now = os.time()
	if launch(1, now, group) == 0 then
		tellAll(group, "Could not summon monsters. Please notify a GM.")
	end
	if table.getn(group) > 1 then
		doPlayerSendTextMessage(cid, MSG, "Group: " .. names(group) .. ". Waves scale with group size.")
	end
	for _, uid in ipairs(left) do
		doPlayerSendCancel(uid, "Group full (max " .. table.getn(ARRIVALS) .. ").")
	end
end

local function nextWave(cid)
	if not inBox(getPlayerPosition(cid), ARENA) then
		return
	end
	local s = scan(ARENA)
	if s.monsters > 0 then
		doPlayerSendCancel(cid, s.monsters .. " monster(s) remaining. Clear the arena first.")
		return
	end
	local cleared, elapsed = currentRun(s.players)
	local startedAt = WaveRun.startedAt
	if startedAt <= 0 then
		startedAt = os.time()
	end
	if cleared > 0 and cleared < table.getn(WAVES) then
		tellAll(s.players, "Wave " .. cleared .. " cleared (" .. formatDuration(elapsed) .. ").")
	end
	for _, uid in ipairs(s.players) do
		record(uid, cleared, elapsed)
	end

	if cleared >= table.getn(WAVES) then
		tellAll(s.players, "You completed all " .. table.getn(WAVES) ..
			" waves of the Jungle Clearing in " .. formatDuration(elapsed) .. "!")
		for _, uid in ipairs(s.players) do
			setPlayerStorageValue(uid, STORAGE_RUN_WAVE, 0)
			setPlayerStorageValue(uid, STORAGE_RUN_START, 0)
			doTeleportThing(uid, CAMP_LANDING)
		end
		doSendMagicEffect(CAMP_LANDING, EFFECT_TELEPORT)
		WaveRun.wave = 0
		WaveRun.startedAt = 0
		return
	end
	launch(cleared + 1, startedAt, s.players)
	doSendMagicEffect(getPlayerPosition(cid), EFFECT_WAVE)
end

local function retire(cid)
	if not inBox(getPlayerPosition(cid), ARENA) then
		return
	end
	local s = scan(ARENA)
	local wave, elapsed = currentRun(s.players)
	local cleared = wave
	if s.monsters > 0 then
		cleared = wave - 1
	end
	record(cid, cleared, elapsed)
	setPlayerStorageValue(cid, STORAGE_RUN_WAVE, 0)
	setPlayerStorageValue(cid, STORAGE_RUN_START, 0)
	doTeleportThing(cid, CAMP_LANDING)
	doSendMagicEffect(CAMP_LANDING, EFFECT_TELEPORT)
	doPlayerSendTextMessage(cid, MSG, "You retired with " .. math.max(cleared, 0) ..
		" cleared wave(s) (" .. formatDuration(elapsed) .. ").")
	if table.getn(s.players) <= 1 then
		WaveRun.wave = 0
		WaveRun.startedAt = 0
	end
end

local function showRank(cid)
	ensureWeek(cid)
	local data = rankLoad()
	local bestWeek = storage(cid, STORAGE_BEST_WEEK)
	local bestTime = storage(cid, STORAGE_BEST_WEEK_TIME)
	local bestStr = tostring(bestWeek)
	if bestWeek > 0 and bestTime > 0 then
		bestStr = bestStr .. " (" .. formatDuration(bestTime) .. ")"
	end
	doPlayerSendTextMessage(cid, MSG, "Wave Arena - weekly ranking. Your best: " .. bestStr ..
		" (weekly) / " .. storage(cid, STORAGE_BEST_ALL) .. " (all-time).")
	local list = rankSorted(data)
	if table.getn(list) == 0 then
		doPlayerSendTextMessage(cid, MSG, "No scores this week. Be the first!")
	end
	for i = 1, math.min(5, table.getn(list)) do
		local e = list[i]
		local line = i .. ") " .. e.name .. " - wave " .. e.wave
		if e.time > 0 then
			line = line .. " (" .. formatDuration(e.time) .. ")"
		end
		doPlayerSendTextMessage(cid, MSG, line)
	end
	local s = scan(ARENA)
	if table.getn(s.players) > 0 then
		local w = currentRun(s.players)
		doPlayerSendTextMessage(cid, MSG, "In the clearing: " .. names(s.players) ..
			" (wave " .. w .. "/" .. table.getn(WAVES) .. ", " .. s.monsters .. " alive).")
	elseif s.monsters > 0 then
		doPlayerSendTextMessage(cid, MSG, "The clearing is resetting (" .. s.monsters .. " monster(s)). Free shortly.")
	else
		doPlayerSendTextMessage(cid, MSG, "The clearing is free.")
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
