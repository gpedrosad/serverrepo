-- Kaelen — Clearing Watcher (Wave Arena camp, 603, 220, 7). Pure ASCII (7.6 client).
--
-- Responsibilities:
--   1. Automatic cleanup: removes orphan monsters in ARENA ~2 s after all players leave/die.
--   2. Live HUD: shows remaining monster count to players inside and a red notice on wave clear.
--   3. Camp info: rules, weekly rewards, and current clearing status.

ARENA = {x0 = 600, y0 = 205, x1 = 612, y1 = 215, z = 7}
TOTAL_WAVES = 20
STORAGE_RUN_WAVE = 9303
CLEANUP_DELAY_TICKS = 2

FX_PUFF = 2
MSG_SMALLINFO = 23
MSG_RED_INFO = 18

empty_ticks = 0
last_wave = 0
saw_mobs_wave = 0
clear_announced_wave = 0
last_players_count = 0
last_monsters_count = 0

RULES = 'Wave Arena: 20 progressive waves (lvl 25 to 100+) with a boss every 5. '
	.. 'Stand on the wooden platform and pull the left lever to enter (up to 7). '
	.. 'Every cleared wave is saved; the weekly ranking breaks ties by fastest time.'

REWARDS_TEXT = 'Weekly rewards (once per week per milestone): '
	.. 'wave 5: 10 platinum + 1 small emerald; '
	.. 'wave 10: 30 platinum + 2 small sapphires; '
	.. 'wave 15: 1 crystal + 3 small rubies; '
	.. 'wave 20: 3 crystals + 5 small diamonds.'

local function isPlayerCid(cid)
	if cid == nil or cid == 0 or isMonster(cid) then
		return false
	end
	local name = creatureGetName(cid)
	return name ~= nil and name ~= '' and name ~= 'Kaelen'
end

local function scanArena()
	local players = {}
	local monsters = {}
	for x = ARENA.x0, ARENA.x1 do
		for y = ARENA.y0, ARENA.y1 do
			local pos = {x = x, y = y, z = ARENA.z}
			local cid = getTopCreature(pos)
			if cid ~= 0 then
				if isMonster(cid) then
					table.insert(monsters, {cid = cid, pos = pos})
				elseif isPlayerCid(cid) then
					table.insert(players, cid)
				end
			end
		end
	end
	return players, monsters
end

local function currentWave(players)
	local w = 0
	for i = 1, table.getn(players) do
		local v = getPlayerStorageValue(players[i], STORAGE_RUN_WAVE)
		if v > w then
			w = v
		end
	end
	return w
end

local function clearOrphanMonsters(monsters)
	for i = 1, table.getn(monsters) do
		doSendMagicEffect(monsters[i].pos, FX_PUFF)
		doRemoveCreature(monsters[i].cid)
	end
end

local function arenaStatusText()
	local players, monsters = scanArena()
	local pCount = table.getn(players)
	local mCount = table.getn(monsters)
	if pCount > 0 then
		local w = currentWave(players)
		return 'Clearing occupied (' .. pCount .. ' player(s), wave ' .. w .. '/' .. TOTAL_WAVES
			.. ', ' .. mCount .. ' monster(s) alive).'
	elseif mCount > 0 then
		return 'Resetting ' .. mCount .. ' leftover monster(s). Free in a moment.'
	end
	return 'The clearing is free and ready.'
end

local function kaelenThink()
	local players, monsters = scanArena()
	local pCount = table.getn(players)
	local mCount = table.getn(monsters)
	last_players_count = pCount
	last_monsters_count = mCount

	if pCount == 0 then
		last_wave = 0
		saw_mobs_wave = 0
		clear_announced_wave = 0
		if mCount > 0 then
			empty_ticks = empty_ticks + 1
			if empty_ticks >= CLEANUP_DELAY_TICKS then
				clearOrphanMonsters(monsters)
				empty_ticks = 0
				last_monsters_count = 0
			end
		else
			empty_ticks = 0
		end
	else
		empty_ticks = 0
		local w = currentWave(players)
		if w ~= last_wave then
			last_wave = w
			saw_mobs_wave = 0
			clear_announced_wave = 0
		end
		if w > 0 then
			if mCount > 0 then
				saw_mobs_wave = w
				local hud = 'Wave Arena | Wave ' .. w .. '/' .. TOTAL_WAVES .. ' | ' .. mCount .. ' monster(s) left'
				for i = 1, pCount do
					doPlayerSendTextMessage(players[i], MSG_SMALLINFO, hud)
				end
			else
				local hud = 'Wave Arena | Wave ' .. w .. '/' .. TOTAL_WAVES .. ' cleared! Pull left for next or right to retire'
				for i = 1, pCount do
					doPlayerSendTextMessage(players[i], MSG_SMALLINFO, hud)
				end
				if saw_mobs_wave == w and clear_announced_wave ~= w then
					clear_announced_wave = w
					local notice = 'Wave Arena: wave ' .. w .. ' cleared! Left lever: next wave. Right lever: retire.'
					if w >= TOTAL_WAVES then
						notice = 'Wave Arena: wave ' .. TOTAL_WAVES .. ' cleared! Pull the left lever to claim victory!'
					end
					for i = 1, pCount do
						doPlayerSendTextMessage(players[i], MSG_RED_INFO, notice)
					end
				end
			end
		end
	end

	npcOnThink(45, 'Good hunting in the clearing.')
end

local function onMessage(cid, msg)
	if npcIsHelp(msg) or msgcontains(msg, 'reglas') or msgcontains(msg, 'rules') then
		selfSay(RULES)
	elseif msgcontains(msg, 'premio') or msgcontains(msg, 'premios')
		or msgcontains(msg, 'reward') or msgcontains(msg, 'rewards')
		or msgcontains(msg, 'recompensa') or msgcontains(msg, 'recompensas') then
		selfSay(REWARDS_TEXT)
	elseif msgcontains(msg, 'estado') or msgcontains(msg, 'status') or msgcontains(msg, 'claro')
		or msgcontains(msg, 'arena') or msgcontains(msg, 'oleada') or msgcontains(msg, 'oleadas')
		or msgcontains(msg, 'wave') or msgcontains(msg, 'waves') then
		selfSay(arenaStatusText())
	end
end

npcDefine{
	greet = function(cid)
		return 'Hello ' .. creatureGetName(cid) .. '! I watch over the Jungle Clearing. '
			.. arenaStatusText() .. ' Say "rules", "rewards", or "status".'
	end,
	busy = 'One moment...',
	onMessage = onMessage,
	onThink = kaelenThink,
}
