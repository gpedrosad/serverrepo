-- Chronos — Reloj de Arena (sala compartida, fases globales).
-- Timer tipo trainers: MSG_SMALLINFO cada think (~1 s) con "quedan X s".
-- Requiere bindings NPC YUR_NPC_EXT: doSummonCreature, doRemoveCreature,
-- doSendMagicEffect, getTopCreature, isMonster.

dofile('data/npc/scripts/lib/npc.lua')

focus = 0
talk_start = 0
target = 0
following = false
attacking = false

-- Sala (debe coincidir con generate-sand-clock.py)
ROOM = {x0 = 330, y0 = 385, x1 = 346, y1 = 399, z = 6}
PHASE_SEC = 120

-- Fases globales: todos viven el mismo evento.
-- Packs rage (Angry/Furious/Enraged) + customs raros (Fury/Wrath).
-- Cantidades para sala compartida ~17x15 (sin spam).
PHASES = {
	{
		name = "Scarab Nest",
		mobs = {{"Angry Scarab", 3}, {"Furious Ancient Scarab", 1}, {"Bone Beast", 2}},
	},
	{
		name = "Huntress Rage",
		mobs = {{"Angry Amazon", 3}, {"Furious Valkyrie", 2}, {"Angry Hunter", 1}},
	},
	{
		name = "Orc Legion",
		mobs = {{"Angry Orc Berserker", 3}, {"Angry Orc Shaman", 2}, {"Furious Orc Leader", 1}},
	},
	{
		name = "Steel & Venom",
		mobs = {{"Angry Hero", 2}, {"Angry Gargoyle", 2}, {"Furious Giant Spider", 1}, {"Angry Black Knight", 1}},
	},
	{
		name = "Necropolis",
		mobs = {{"Angry Vampire", 2}, {"Furious Necromancer", 1}, {"Angry Lich", 1}, {"Furious Warlock", 1}},
	},
	{
		name = "Abyssal Peak",
		mobs = {{"Angry Demon", 1}, {"Fury", 1}, {"Wrath", 1}},
	},
}

SPAWN_SPOTS = {
	{x = 334, y = 389, z = 6},
	{x = 338, y = 389, z = 6},
	{x = 342, y = 389, z = 6},
	{x = 334, y = 392, z = 6},
	{x = 338, y = 392, z = 6},
	{x = 342, y = 392, z = 6},
	{x = 334, y = 395, z = 6},
	{x = 338, y = 395, z = 6},
	{x = 342, y = 395, z = 6},
	{x = 336, y = 391, z = 6},
	{x = 340, y = 391, z = 6},
	{x = 336, y = 393, z = 6},
	{x = 340, y = 393, z = 6},
}

-- Efectos 7.6
FX_PUFF = 2
FX_RINGS = 7
FX_ENERGY = 10
FX_POP = 11
FX_CLOUD = 20

MSG_SMALLINFO = 23 -- 0x17
MSG_RED_INFO = 18  -- 0x12

current_phase = 0
room_players = {}

function sandClockInRoom(x, y, z)
	return z == ROOM.z
		and x >= ROOM.x0 and x <= ROOM.x1
		and y >= ROOM.y0 and y <= ROOM.y1
end

function sandClockPhaseIndex()
	local n = table.getn(PHASES)
	return math.mod(math.floor(os.time() / PHASE_SEC), n) + 1
end

function sandClockRemainSec()
	return PHASE_SEC - math.mod(os.time(), PHASE_SEC)
end

function sandClockFormatRemain(sec)
	-- Igual que trainers: siempre en segundos cuando < 60;
	-- si no, "X min Y s" (formatTrainingTime).
	if sec < 0 then
		sec = 0
	end
	local min = math.floor(sec / 60)
	local s = math.mod(sec, 60)
	if min > 0 then
		return min .. " min " .. s .. " s"
	end
	return s .. " s"
end

function sandClockIsPlayerCid(cid)
	if cid == nil or cid == 0 then
		return false
	end
	if isMonster(cid) then
		return false
	end
	local name = creatureGetName(cid)
	if name == nil or name == '' or name == 'Chronos' then
		return false
	end
	return true
end

function sandClockGreet(cid)
	local phase = PHASES[sandClockPhaseIndex()]
	local remain = sandClockFormatRemain(sandClockRemainSec())
	doPlayerSendTextMessage(cid, MSG_RED_INFO,
		'Reloj de Arena: fase ' .. phase.name .. '. Quedan ' .. remain .. '.')
end

function sandClockTrackPlayer(cid)
	if not sandClockIsPlayerCid(cid) then
		return
	end
	local x, y, z = creatureGetPosition(cid)
	if x == nil then
		room_players[cid] = nil
		return
	end
	if sandClockInRoom(x, y, z) then
		local was = room_players[cid]
		room_players[cid] = true
		if not was then
			sandClockGreet(cid)
		end
	else
		room_players[cid] = nil
	end
end

function sandClockScanRoomPlayers()
	local x, y, cid
	local seen = {}
	for x = ROOM.x0, ROOM.x1 do
		for y = ROOM.y0, ROOM.y1 do
			cid = getTopCreature({x = x, y = y, z = ROOM.z})
			if sandClockIsPlayerCid(cid) then
				seen[cid] = true
				sandClockTrackPlayer(cid)
			end
		end
	end
	local old, _
	for old, _ in pairs(room_players) do
		if not seen[old] then
			room_players[old] = nil
		end
	end
end

function sandClockBroadcast(msgClass, text)
	local cid, _
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
	local x, y, cid
	for x = ROOM.x0, ROOM.x1 do
		for y = ROOM.y0, ROOM.y1 do
			cid = getTopCreature({x = x, y = y, z = ROOM.z})
			if cid ~= 0 and isMonster(cid) then
				table.insert(toRemove, cid)
			end
		end
	end
	local i
	for i = 1, table.getn(toRemove) do
		doRemoveCreature(toRemove[i])
	end
end

function sandClockSpawnPhase(phase)
	local spot = 1
	local i, n, name, pos
	for i = 1, table.getn(phase.mobs) do
		name = phase.mobs[i][1]
		for n = 1, phase.mobs[i][2] do
			pos = SPAWN_SPOTS[((spot - 1) % table.getn(SPAWN_SPOTS)) + 1]
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

function sandClockApplyPhase(idx, announce)
	local phase = PHASES[idx]
	if phase == nil then
		return
	end
	sandClockClearMonsters()
	sandClockSpawnPhase(phase)
	current_phase = idx
	if announce then
		selfSay('Nueva fase: ' .. phase.name .. '!')
		sandClockBroadcast(MSG_RED_INFO, 'Reloj de Arena: nueva fase — ' .. phase.name .. '.')
	end
end

function sandClockEnsure()
	local idx = sandClockPhaseIndex()
	if current_phase == 0 then
		sandClockApplyPhase(idx, false)
	elseif idx ~= current_phase then
		sandClockApplyPhase(idx, true)
	end
end

function onThingMove(creature, thing, oldpos, oldstackpos)
end

function onCreatureAppear(creature)
	sandClockTrackPlayer(creature)
end

function onCreatureDisappear(cid, pos)
	room_players[cid] = nil
	npcOnCreatureDisappear(cid)
end

function onCreatureTurn(creature)
end

function onCreatureChangeOutfit(creature)
end

function onCreatureSay(cid, type, msg)
	msg = string.lower(msg)
	local state = npcHandleMessage(
		cid,
		msg,
		'Hi ' .. creatureGetName(cid) .. '! Esta sala cambia de fase sola. Di "time" o "fase".',
		'Un momento...'
	)
	if state ~= 'focused' then
		return
	end

	if msgcontains(msg, 'time') or msgcontains(msg, 'tiempo') or msgcontains(msg, 'fase')
		or msgcontains(msg, 'phase') or msgcontains(msg, 'reloj') or npcIsHelp(msg) then
		local phase = PHASES[sandClockPhaseIndex()]
		local remain = sandClockFormatRemain(sandClockRemainSec())
		selfSay('Fase actual: ' .. phase.name .. '. Quedan ' .. remain .. ' para el cambio.')
	end
end

function onThink()
	sandClockScanRoomPlayers()
	sandClockEnsure()

	local phase = PHASES[current_phase]
	if phase == nil then
		return
	end

	local remain = sandClockFormatRemain(sandClockRemainSec())
	local line = 'Reloj: quedan ' .. remain .. ' | fase: ' .. phase.name
	sandClockBroadcast(MSG_SMALLINFO, line)

	npcOnThink(45, '...')
end
