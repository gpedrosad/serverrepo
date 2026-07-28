-- Leech — Bleed Room (mana drain + cadena de 10 mobs).
-- UI tipo trainers: MSG_SMALLINFO cada think (~1 s).
-- Requiere bindings NPC YUR_NPC_EXT: doSummonCreature, doRemoveCreature,
-- doSendMagicEffect, getTopCreature, isMonster, getPlayerMana, doPlayerAddMana.

dofile('data/npc/scripts/lib/npc.lua')

focus = 0
talk_start = 0
target = 0
following = false
attacking = false

-- Debe coincidir con generate-bleed-room.py (sala 5x5)
ROOM = {x0 = 353, y0 = 388, x1 = 357, y1 = 392, z = 6}
SPAWN = {x = 355, y = 390, z = 6}
MANA_DRAIN = 8 -- por think (~1 s)

-- 10 mobs, cada kill spawnea el siguiente (mas fuerte).
MOBS = {
	"Rat",
	"Rotworm",
	"Skeleton",
	"Orc Warrior",
	"Cyclops",
	"Beholder",
	"Dragon",
	"Hero",
	"Dragon Lord",
	"Demon",
}

FX_PUFF = 2
FX_RINGS = 7
FX_ENERGY = 10
FX_POP = 11
FX_CLOUD = 20

MSG_SMALLINFO = 23 -- 0x17
MSG_RED_INFO = 18  -- 0x12

room_players = {}
bleed_wave = 0      -- 0 idle, 1..10 activo, 11 victoria breve
bleed_mob = 0
bleed_victory_until = 0

function bleedInRoom(x, y, z)
	return z == ROOM.z
		and x >= ROOM.x0 and x <= ROOM.x1
		and y >= ROOM.y0 and y <= ROOM.y1
end

function bleedIsPlayerCid(cid)
	if cid == nil or cid == 0 then
		return false
	end
	if isMonster(cid) then
		return false
	end
	local name = creatureGetName(cid)
	if name == nil or name == '' or name == 'Leech' then
		return false
	end
	return true
end

function bleedMobAlive()
	if bleed_mob == nil or bleed_mob == 0 then
		return false
	end
	if not isMonster(bleed_mob) then
		return false
	end
	local x, y, z = creatureGetPosition(bleed_mob)
	if x == nil then
		return false
	end
	return bleedInRoom(x, y, z)
end

function bleedClearMonsters()
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
	bleed_mob = 0
end

function bleedBroadcast(msgClass, text)
	local cid, _
	for cid, _ in pairs(room_players) do
		local x, y, z = creatureGetPosition(cid)
		if x ~= nil and bleedInRoom(x, y, z) and bleedIsPlayerCid(cid) then
			doPlayerSendTextMessage(cid, msgClass, text)
		else
			room_players[cid] = nil
		end
	end
end

function bleedPlayerCount()
	local n = 0
	local cid, _
	for cid, _ in pairs(room_players) do
		local x, y, z = creatureGetPosition(cid)
		if x ~= nil and bleedInRoom(x, y, z) and bleedIsPlayerCid(cid) then
			n = n + 1
		else
			room_players[cid] = nil
		end
	end
	return n
end

function bleedSpawnWave(idx)
	local name = MOBS[idx]
	if name == nil then
		return false
	end
	bleedClearMonsters()
	doSendMagicEffect(SPAWN, FX_CLOUD)
	doSendMagicEffect(SPAWN, FX_RINGS)
	local cid = doSummonCreature(name, SPAWN)
	if cid ~= 0 then
		bleed_mob = cid
		doSendMagicEffect(SPAWN, FX_POP)
		doSendMagicEffect(SPAWN, FX_ENERGY)
		return true
	end
	doSendMagicEffect(SPAWN, FX_PUFF)
	bleed_mob = 0
	return false
end

function bleedReset()
	bleedClearMonsters()
	bleed_wave = 0
	bleed_victory_until = 0
end

function bleedStart()
	bleed_wave = 1
	bleed_victory_until = 0
	if bleedSpawnWave(1) then
		bleedBroadcast(MSG_RED_INFO, 'Bleed Room: 1/10 ' .. MOBS[1] .. '. Mana -' .. MANA_DRAIN .. '/s.')
		selfSay('Bleed starts. Survive the chain.')
	else
		bleedReset()
	end
end

function bleedAdvance()
	local nextWave = bleed_wave + 1
	local total = table.getn(MOBS)
	if nextWave > total then
		bleedClearMonsters()
		bleed_wave = 11
		bleed_victory_until = os.time() + 8
		bleedBroadcast(MSG_RED_INFO, 'Bleed Room: CLEAR! 10/10. Exit south or wait for reset.')
		selfSay('Chain complete!')
		return
	end
	bleed_wave = nextWave
	if bleedSpawnWave(nextWave) then
		bleedBroadcast(MSG_RED_INFO, 'Bleed Room: ' .. nextWave .. '/' .. total .. ' ' .. MOBS[nextWave] .. '.')
	else
		bleedBroadcast(MSG_RED_INFO, 'Bleed Room: spawn failed, resetting.')
		bleedReset()
	end
end

function bleedGreet(cid)
	doPlayerSendTextMessage(cid, MSG_RED_INFO,
		'Bleed Room: mana -' .. MANA_DRAIN .. '/s. Kill to advance (10 mobs).')
end

function bleedTrackPlayer(cid)
	if not bleedIsPlayerCid(cid) then
		return
	end
	local x, y, z = creatureGetPosition(cid)
	if x == nil then
		room_players[cid] = nil
		return
	end
	if bleedInRoom(x, y, z) then
		local was = room_players[cid]
		room_players[cid] = true
		if not was then
			bleedGreet(cid)
		end
	else
		room_players[cid] = nil
	end
end

function bleedScanRoomPlayers()
	local x, y, cid
	local seen = {}
	for x = ROOM.x0, ROOM.x1 do
		for y = ROOM.y0, ROOM.y1 do
			cid = getTopCreature({x = x, y = y, z = ROOM.z})
			if bleedIsPlayerCid(cid) then
				seen[cid] = true
				bleedTrackPlayer(cid)
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

function bleedDrainMana()
	local cid, _
	for cid, _ in pairs(room_players) do
		local x, y, z = creatureGetPosition(cid)
		if x ~= nil and bleedInRoom(x, y, z) and bleedIsPlayerCid(cid) then
			local mana = getPlayerMana(cid)
			if mana == nil then
				mana = 0
			end
			if mana > 0 then
				local lose = MANA_DRAIN
				if lose > mana then
					lose = mana
				end
				doPlayerAddMana(cid, -lose)
			end
		else
			room_players[cid] = nil
		end
	end
end

function bleedHudLine(cid)
	local mana = getPlayerMana(cid)
	if mana == nil then
		mana = 0
	end
	local total = table.getn(MOBS)
	if bleed_wave == 0 then
		return 'Bleed: idle | mana ' .. mana .. ' (-' .. MANA_DRAIN .. '/s)'
	end
	if bleed_wave == 11 then
		local left = bleed_victory_until - os.time()
		if left < 0 then
			left = 0
		end
		return 'Bleed: CLEAR | reset in ' .. left .. ' s | mana ' .. mana
	end
	local name = MOBS[bleed_wave]
	if name == nil then
		name = '?'
	end
	return 'Bleed: ' .. bleed_wave .. '/' .. total .. ' ' .. name
		.. ' | mana ' .. mana .. ' (-' .. MANA_DRAIN .. '/s)'
end

function bleedSendHud()
	local cid, _
	for cid, _ in pairs(room_players) do
		local x, y, z = creatureGetPosition(cid)
		if x ~= nil and bleedInRoom(x, y, z) and bleedIsPlayerCid(cid) then
			doPlayerSendTextMessage(cid, MSG_SMALLINFO, bleedHudLine(cid))
		else
			room_players[cid] = nil
		end
	end
end

function bleedEnsure()
	local n = bleedPlayerCount()

	if bleed_wave == 11 then
		if os.time() >= bleed_victory_until then
			bleedReset()
		end
		if n == 0 then
			bleedReset()
		end
		return
	end

	if n == 0 then
		if bleed_wave > 0 then
			bleedReset()
		end
		return
	end

	if bleed_wave == 0 then
		bleedStart()
		return
	end

	if not bleedMobAlive() then
		bleedAdvance()
	end
end

function onThingMove(creature, thing, oldpos, oldstackpos)
end

function onCreatureAppear(creature)
	bleedTrackPlayer(creature)
end

function onCreatureDisappear(cid, pos)
	room_players[cid] = nil
	if cid == bleed_mob then
		bleed_mob = 0
	end
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
		'Hi ' .. creatureGetName(cid) .. '! Mana bleeds here. Kill to climb 10 mobs. Say "status".',
		'One moment...'
	)
	if state ~= 'focused' then
		return
	end

	if msgcontains(msg, 'status') or msgcontains(msg, 'bleed') or msgcontains(msg, 'mana')
		or npcIsHelp(msg) then
		selfSay(bleedHudLine(cid))
	end
end

function onThink()
	bleedScanRoomPlayers()
	bleedDrainMana()
	bleedEnsure()
	bleedSendHud()
	npcOnThink(45, '...')
end
