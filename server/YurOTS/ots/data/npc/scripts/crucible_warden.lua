-- Varkon — Crucible Warden (Sala del Crisol, PZ). Pure ASCII (7.6 client).
-- Corre las 3 arenas del Crisol; las palancas (data/actions/scripts/crucible.lua) solo validan y
-- mandan al grupo con un pase. Config compartida: data/actions/lib/crucible.lua.
--
-- Por arena (independientes, pueden correr 3 grupos a la vez):
--   IDLE     vacía. Si aparecen jugadores: los que no tienen pase (relog adentro, GM) vuelven a la sala;
--            con al menos uno con pase -> PREP.
--   PREP     PREP_SEC de cuenta regresiva y aparece el elite/jefe del día con su escolta -> ACTIVE.
--   ACTIVE   contador abajo de la pantalla. Si muere el jefe de Oro, todos los de adentro quedan
--            marcados (una vez por día). Sin enemigos -> CLEARED: premio diario y se abre la puerta siguiente.
--   CLEARED  CLEARED_SEC para lootear; después vuelven todos a la sala.
--   Sin jugadores adentro (murieron, salieron) durante EMPTY_SEC: se borran los monstruos -> IDLE.
--   Cada corrida empieza limpia: nunca se acumulan elites ni jefes.

dofile('data/actions/lib/crucible.lua')

PREP_SEC = 5
CLEARED_SEC = 60
EMPTY_SEC = 3

MSG_RED_INFO = 18
MSG_SMALLINFO = 23

FX_PUFF = 2
FX_ENERGY = 10
FX_TELEPORT = 11
FX_FIRE = 15

-- estado por puerta
runs = {}

local function resetRun(door)
	runs[door] = {state = 'IDLE', untilTime = 0, mobs = {}, boss = 0, bossName = '', bossDown = false, empty = 0}
end

for _, door in ipairs(CRUCIBLE.order) do
	resetRun(door)
end

local function isRageName(name)
	return name ~= nil and (string.sub(name, 1, 6) == 'Angry ' or string.sub(name, 1, 8) == 'Furious '
		or string.sub(name, 1, 8) == 'Enraged ')
end

local function isPlayerCid(cid)
	if cid == nil or cid == 0 or isMonster(cid) then
		return false
	end
	local name = creatureGetName(cid)
	return name ~= nil and name ~= '' and name ~= 'Varkon'
end

-- jugadores {cid...} y monstruos {{cid, pos, name}...} dentro de la arena
local function scanArena(arena)
	local players, monsters = {}, {}
	for x = arena.x0, arena.x1 do
		for y = arena.y0, arena.y1 do
			local pos = {x = x, y = y, z = arena.z}
			local cid = getTopCreature(pos)
			if cid ~= 0 then
				if isMonster(cid) then
					table.insert(monsters, {cid = cid, pos = pos, name = creatureGetName(cid)})
				elseif isPlayerCid(cid) then
					table.insert(players, cid)
				end
			end
		end
	end
	return players, monsters
end

local function tell(players, class, text)
	for _, cid in ipairs(players) do
		doPlayerSendTextMessage(cid, class, text)
	end
end

local function sendToHall(cid)
	travelPlayerTo(cid, CRUCIBLE.landing.x, CRUCIBLE.landing.y, CRUCIBLE.landing.z)
	doSendMagicEffect(CRUCIBLE.landing, FX_TELEPORT)
end

local function enemiesLeft(run, monsters)
	local n = 0
	for cid, _ in pairs(run.mobs) do
		if isMonster(cid) then
			n = n + 1
		else
			run.mobs[cid] = nil
		end
	end
	for _, m in ipairs(monsters) do
		if not run.mobs[m.cid] and isRageName(m.name) then
			n = n + 1                                   -- un monstruo de la corrida revivió furioso
		end
	end
	return n
end

local function clearArena(door, monsters)
	for _, m in ipairs(monsters) do
		doSendMagicEffect(m.pos, FX_PUFF)
		doRemoveCreature(m.cid)
	end
	resetRun(door)
end

-- Invoca una criatura en su punto o, si está ocupado, en el primer punto libre de la arena.
local function summonAt(name, spots, first, used)
	local order = {first}
	for i = 1, table.getn(spots) do
		if i ~= first then
			table.insert(order, i)
		end
	end
	for _, i in ipairs(order) do
		if not used[i] then
			local cid = doSummonCreature(name, spots[i])
			if cid ~= 0 then
				used[i] = true
				doSendMagicEffect(spots[i], FX_TELEPORT)
				return cid
			end
		end
	end
	return 0
end

local function spawnRun(door, players)
	local run, tier, arena = runs[door], CRUCIBLE.tiers[door], CRUCIBLE.arenas[door]
	local elite = crucibleToday()[door]
	local used = {}
	run.boss = summonAt(elite, arena.spawns, 1, used)
	run.bossName = elite
	if run.boss ~= 0 then
		run.mobs[run.boss] = true
		doSendMagicEffect(arena.spawns[1], FX_FIRE)
	end
	local escorts = table.getn(tier.escort)
	for i = 1, tier.escortCount do
		local cid = summonAt(tier.escort[math.fmod(i - 1, escorts) + 1], arena.spawns, i + 1, used)
		if cid ~= 0 then
			run.mobs[cid] = true
		end
	end
	if next(run.mobs) == nil then
		tell(players, MSG_RED_INFO, 'The Crucible failed to summon monsters. Please contact a GM.')
		return false
	end
	run.state = 'ACTIVE'
	local what = 'Elite'
	if door == 'gold' then
		what = 'Boss'
	end
	tell(players, MSG_RED_INFO, 'FIGHT! ' .. what .. ': ' .. elite .. ' with ' .. tier.escortCount .. ' guards.')
	return true
end

local function onBossDown(door, run, players)
	run.bossDown = true
	if door == 'gold' then
		for _, cid in ipairs(players) do
			setPlayerStorageValue(cid, CRUCIBLE.STORAGE_BOSS_DAY, crucibleDay())
		end
		tell(players, MSG_RED_INFO, run.bossName .. ' has fallen! The Gold boss is done for you today.')
	else
		tell(players, MSG_RED_INFO, 'The elite ' .. run.bossName .. ' has fallen!')
	end
end

local function award(door, players)
	local tier = CRUCIBLE.tiers[door]
	local arena = CRUCIBLE.arenas[door]
	for i = 1, table.getn(arena.spawns) do
		doSendMagicEffect(arena.spawns[i], FX_ENERGY)
	end
	selfSay('The ' .. tier.label .. ' arena has been cleared!')
	for _, cid in ipairs(players) do
		if door == 'gold' then
			setPlayerStorageValue(cid, CRUCIBLE.STORAGE_BOSS_DAY, crucibleDay())
		end
		local text = 'Crucible ' .. tier.label .. ' cleared!'
		if crucibleMarkCleared(cid, door) then
			local r = tier.reward
			local gem = CRUCIBLE.SMALL_GEMS[math.random(1, table.getn(CRUCIBLE.SMALL_GEMS))]
			doPlayerAddMoney(cid, r.gold)
			doPlayerAddExp(cid, r.exp)
			doPlayerAddItem(cid, gem[1], r.gems)
			local gemName = gem[2]
			if r.gems > 1 then
				gemName = gemName .. 's'
			end
			text = text .. ' Reward: ' .. r.gold .. ' gp, ' .. r.exp .. ' exp and ' .. r.gems .. ' ' .. gemName .. '.'
			local nextDoor = CRUCIBLE.order[tier.step + 1]
			if nextDoor then
				text = text .. ' The ' .. CRUCIBLE.tiers[nextDoor].label .. ' gate is now open for you today.'
			else
				text = text .. ' You conquered the Crucible today!'
			end
		else
			text = text .. ' (You already claimed this reward today.)'
		end
		doPlayerSendTextMessage(cid, MSG_RED_INFO, text)
	end
end

-- Recarga del script con una pelea en curso: adopta los monstruos que ya están adentro.
local function adopt(door, monsters)
	local run = runs[door]
	run.state = 'ACTIVE'
	local elite = crucibleToday()[door]
	for _, m in ipairs(monsters) do
		run.mobs[m.cid] = true
		if m.name == elite then
			run.boss = m.cid
			run.bossName = elite
		end
	end
end

local function hud(door, run, players, left)
	local tier = CRUCIBLE.tiers[door]
	local head = 'Crucible ' .. tier.label .. ' | '
	local text
	if run.state == 'PREP' then
		text = head .. run.bossName .. ' arrives in ' .. math.max(0, run.untilTime - os.time()) .. ' s'
	elseif run.state == 'ACTIVE' then
		local who = 'elite'
		if door == 'gold' then
			who = 'boss'
		end
		local bossState = 'alive'
		if run.bossDown or run.boss == 0 then
			bossState = 'down'
		end
		text = head .. who .. ' ' .. run.bossName .. ': ' .. bossState .. ' | ' .. left .. ' enemies left'
	elseif run.state == 'CLEARED' then
		text = head .. 'CLEARED! Back to the hall in ' .. math.max(0, run.untilTime - os.time())
			.. ' s (or take the southern portal)'
	end
	if text then
		tell(players, MSG_SMALLINFO, text)
	end
end

local function thinkArena(door)
	local run = runs[door]
	local arena = CRUCIBLE.arenas[door]
	local players, monsters = scanArena(arena)
	local now = os.time()

	if table.getn(players) == 0 then
		if run.state ~= 'IDLE' or table.getn(monsters) > 0 then
			run.empty = run.empty + 1
			if run.empty >= EMPTY_SEC then
				clearArena(door, monsters)
			end
		end
		return
	end
	run.empty = 0

	if run.state == 'IDLE' then
		if table.getn(monsters) > 0 then
			adopt(door, monsters)
			return
		end
		local allowed = {}
		for _, cid in ipairs(players) do
			if crucibleUseTicket(cid, door) then
				table.insert(allowed, cid)
			else
				doPlayerSendTextMessage(cid, MSG_RED_INFO, 'Enter the Crucible arenas with the levers in the hall.')
				sendToHall(cid)
			end
		end
		if table.getn(allowed) == 0 then
			return
		end
		local tier = CRUCIBLE.tiers[door]
		run.state = 'PREP'
		run.untilTime = now + PREP_SEC
		run.bossName = crucibleToday()[door]
		tell(allowed, MSG_RED_INFO, 'Crucible ' .. tier.label .. ' - ' .. arena.name .. ': ' .. run.bossName
			.. ' and ' .. tier.escortCount .. ' guards arrive in ' .. PREP_SEC .. ' s. Kill them all to clear the arena!')
		hud(door, run, allowed, 0)
		return
	end

	if run.state == 'PREP' then
		if now >= run.untilTime then
			if not spawnRun(door, players) then
				clearArena(door, monsters)
				for _, cid in ipairs(players) do
					sendToHall(cid)
				end
				return
			end
			hud(door, run, players, enemiesLeft(run, {}))
		else
			hud(door, run, players, 0)
		end
		return
	end

	if run.state == 'ACTIVE' then
		if run.boss ~= 0 and not run.bossDown and not isMonster(run.boss) then
			onBossDown(door, run, players)
		end
		local left = enemiesLeft(run, monsters)
		if left == 0 then
			award(door, players)
			run.state = 'CLEARED'
			run.untilTime = now + CLEARED_SEC
		end
		hud(door, run, players, left)
		return
	end

	if run.state == 'CLEARED' then
		if now >= run.untilTime then
			for _, cid in ipairs(players) do
				sendToHall(cid)
			end
			clearArena(door, monsters)
		else
			hud(door, run, players, 0)
		end
	end
end

local function wardenThink()
	for _, door in ipairs(CRUCIBLE.order) do
		thinkArena(door)
	end
	npcOnThink(45, 'Good luck in the arenas.')
end

-------------------------------------------------------------------- diálogo

RULES = 'Three gates, one ladder: Bronze, then Silver, then Gold. Clearing a gate opens the next one '
	.. 'for the rest of the day. Stand on a gate platform with your group (up to 7) and pull its lever. '
	.. 'Kill every monster in the arena to clear it.'

local function rewardsText()
	return 'Once per day per gate: Bronze ' .. crucibleRewardText('bronze') .. '; Silver '
		.. crucibleRewardText('silver') .. '; Gold ' .. crucibleRewardText('gold')
		.. '. The Gold boss can be defeated once per day and may drop its exclusive weapon.'
end

local function statusText()
	local parts = {}
	for _, door in ipairs(CRUCIBLE.order) do
		local run = runs[door]
		local state = 'free'
		if run.state == 'PREP' or run.state == 'ACTIVE' then
			state = 'fighting'
		elseif run.state == 'CLEARED' then
			state = 'just cleared'
		end
		table.insert(parts, CRUCIBLE.tiers[door].label .. ' ' .. state)
	end
	return 'Arenas: ' .. table.concat(parts, ', ') .. '.'
end

local function onMessage(cid, msg)
	if npcIsHelp(msg) or msgcontains(msg, 'rules') or msgcontains(msg, 'reglas') then
		selfSay(RULES)
	elseif npcMatchesAny(msg, {'today', 'hoy', 'boss', 'jefe', 'elite', 'elites'}) then
		selfSay(crucibleLineupText())
	elseif npcMatchesAny(msg, {'progress', 'progreso'}) then
		selfSay('Your progress today: ' .. crucibleProgressText(cid))
	elseif npcMatchesAny(msg, {'reward', 'rewards', 'premio', 'premios', 'recompensa', 'recompensas'}) then
		selfSay(rewardsText())
	elseif npcMatchesAny(msg, {'status', 'estado', 'arena', 'arenas'}) then
		selfSay(statusText())
	end
end

npcDefine{
	greet = function(cid)
		return 'Welcome to the Crucible, ' .. creatureGetName(cid) .. '. Clear Bronze, then Silver, then Gold. '
			.. 'Your progress today: ' .. crucibleProgressText(cid)
			.. ' Ask me about "rules", "today", "rewards" or "status".'
	end,
	busy = 'One moment, fighter...',
	onMessage = onMessage,
	onThink = wardenThink,
}
