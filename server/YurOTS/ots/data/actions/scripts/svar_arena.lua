-- Arena de Fosos (estilo Svargrond 8.x).
-- Lobby: 7300 Greenhorn / 7301 Scrapper / 7302 Warlord / 7303 Info
-- Pits: 7304 Next / 7305 Forfeit
-- Reward chests: 7310 / 7311 / 7312 (elegir uno por dificultad, una vez)
-- Textos ASCII (cliente 7.6).

UID_GREEN = 7300
UID_SCRAP = 7301
UID_WAR = 7302
UID_INFO = 7303
UID_NEXT = 7304
UID_FORFEIT = 7305
UID_CHEST_A = 7310
UID_CHEST_B = 7311
UID_CHEST_C = 7312

STORAGE_CLAIM_GREEN = 9410
STORAGE_CLAIM_SCRAP = 9411
STORAGE_CLAIM_WAR = 9412
STORAGE_RUN_DIFF = 9413
STORAGE_RUN_READY = 9414

PIT_TIME_SEC = 360
N_PITS = 10

FEES = {
	[1] = 1000,
	[2] = 5000,
	[3] = 10000,
}

DIFF_NAME = {
	[1] = "Greenhorn",
	[2] = "Scrapper",
	[3] = "Warlord",
}

CLAIM_STORAGE = {
	[1] = STORAGE_CLAIM_GREEN,
	[2] = STORAGE_CLAIM_SCRAP,
	[3] = STORAGE_CLAIM_WAR,
}

-- 10 bosses por dificultad (nombres exactos de monsters.xml)
BOSSES = {
	[1] = {
		"Rat", "Wolf", "Bear", "Orc", "Amazon",
		"Valkyrie", "Cyclops", "Dwarf Guard", "Minotaur Guard", "Giant Spider",
	},
	[2] = {
		"Amazon", "Valkyrie", "Cyclops", "Dwarf Guard", "Minotaur Guard",
		"Black Knight", "Giant Spider", "Dragon", "Hero", "Necromancer",
	},
	[3] = {
		"Black Knight", "Dragon", "Hero", "Necromancer", "Priestess",
		"Dragon Lord", "Warlock", "Hydra", "Behemoth", "Demon",
	},
}

-- 3 premios por dificultad (mismo orden que cofres A/B/C)
REWARDS = {
	[1] = {2160, 2392, 2476}, -- crystal coin, fire sword, knight armor
	[2] = {2400, 2472, 2195}, -- magic sword, magic plate armor, boots of haste
	[3] = {2493, 2520, 2415}, -- demon helmet, demon shield, great axe
}

PITS = {
	{x0 = 218, y0 = 390, x1 = 222, y1 = 394, z = 6, entry = {x = 220, y = 392, z = 6}},
	{x0 = 225, y0 = 390, x1 = 229, y1 = 394, z = 6, entry = {x = 227, y = 392, z = 6}},
	{x0 = 232, y0 = 390, x1 = 236, y1 = 394, z = 6, entry = {x = 234, y = 392, z = 6}},
	{x0 = 239, y0 = 390, x1 = 243, y1 = 394, z = 6, entry = {x = 241, y = 392, z = 6}},
	{x0 = 246, y0 = 390, x1 = 250, y1 = 394, z = 6, entry = {x = 248, y = 392, z = 6}},
	{x0 = 253, y0 = 390, x1 = 257, y1 = 394, z = 6, entry = {x = 255, y = 392, z = 6}},
	{x0 = 260, y0 = 390, x1 = 264, y1 = 394, z = 6, entry = {x = 262, y = 392, z = 6}},
	{x0 = 267, y0 = 390, x1 = 271, y1 = 394, z = 6, entry = {x = 269, y = 392, z = 6}},
	{x0 = 274, y0 = 390, x1 = 278, y1 = 394, z = 6, entry = {x = 276, y = 392, z = 6}},
	{x0 = 281, y0 = 390, x1 = 285, y1 = 394, z = 6, entry = {x = 283, y = 392, z = 6}},
}

LOBBY = {x0 = 200, y0 = 390, x1 = 214, y1 = 400, z = 6}
REWARD_ROOM = {x0 = 200, y0 = 403, x1 = 214, y1 = 412, z = 6}
REWARD_ENTRY = {x = 207, y = 408, z = 6}
LANDING = {x = 205, y = 396, z = 6}
TEMPLE = {x = 163, y = 54, z = 7}

if not SvarArenaState then
	SvarArenaState = {
		owner = 0,
		ownerName = "",
		diff = 0,
		pit = 0,
		pitEnter = 0,
	}
end

function svarInBox(pos, box)
	return pos.x >= box.x0 and pos.x <= box.x1
		and pos.y >= box.y0 and pos.y <= box.y1
		and pos.z == box.z
end

function svarPlayerPos(cid)
	return getPlayerPosition(cid)
end

function svarInLobby(cid)
	return svarInBox(svarPlayerPos(cid), LOBBY)
end

function svarInReward(cid)
	return svarInBox(svarPlayerPos(cid), REWARD_ROOM)
end

function svarInAnyPit(cid)
	local pos = svarPlayerPos(cid)
	local i
	for i = 1, N_PITS do
		if svarInBox(pos, PITS[i]) then
			return i
		end
	end
	return 0
end

function svarCountMonsters(box)
	local count = 0
	local x, y
	for x = box.x0, box.x1 do
		for y = box.y0, box.y1 do
			local th = getThingfromPos({x = x, y = y, z = box.z, stackpos = 253})
			if th.itemid > 0 then
				count = count + 1
			end
		end
	end
	return count
end

function svarClearOwnerIfGone()
	if SvarArenaState.owner == 0 then
		return
	end
	local cid = SvarArenaState.owner
	if not svarInLobby(cid) and svarInAnyPit(cid) == 0 and not svarInReward(cid) then
		SvarArenaState.owner = 0
		SvarArenaState.ownerName = ""
		SvarArenaState.diff = 0
		SvarArenaState.pit = 0
		SvarArenaState.pitEnter = 0
	end
end

function svarResetRun()
	SvarArenaState.owner = 0
	SvarArenaState.ownerName = ""
	SvarArenaState.diff = 0
	SvarArenaState.pit = 0
	SvarArenaState.pitEnter = 0
end

function svarRemoveMoney(cid, amount)
	return doPlayerRemoveMoney(cid, amount) == 1
end

function svarSpawnBoss(diff, pitIndex)
	local box = PITS[pitIndex]
	local name = BOSSES[diff][pitIndex]
	local pos = {x = box.entry.x, y = box.entry.y, z = box.z}
	return doSummonCreature(name, pos) ~= 0
end

function svarStart(cid, diff)
	svarClearOwnerIfGone()

	if not svarInLobby(cid) then
		doPlayerSendCancel(cid, "Usa la palanca desde el lobby de los Fosos.")
		return
	end

	if SvarArenaState.owner ~= 0 and SvarArenaState.owner ~= cid then
		if svarInLobby(SvarArenaState.owner) or svarInAnyPit(SvarArenaState.owner) > 0 or svarInReward(SvarArenaState.owner) then
			doPlayerSendCancel(cid, "Corrida activa de " .. SvarArenaState.ownerName .. ".")
			return
		end
	end

	local fee = FEES[diff]
	if not svarRemoveMoney(cid, fee) then
		doPlayerSendCancel(cid, "Necesitas " .. fee .. " gold.")
		return
	end

	-- limpiar pit 1 si quedo basura
	if svarCountMonsters(PITS[1]) > 0 then
		doPlayerSendCancel(cid, "Pit 1 ocupado. Espera o avisa a un GM.")
		return
	end

	if not svarSpawnBoss(diff, 1) then
		doPlayerSendCancel(cid, "No se pudo invocar el boss. Avisa a un GM.")
		return
	end

	SvarArenaState.owner = cid
	SvarArenaState.ownerName = getPlayerName(cid)
	SvarArenaState.diff = diff
	SvarArenaState.pit = 1
	SvarArenaState.pitEnter = os.time()
	setPlayerStorageValue(cid, STORAGE_RUN_DIFF, diff)
	setPlayerStorageValue(cid, STORAGE_RUN_READY, 0)

	doTeleportThing(cid, PITS[1].entry)
	doSendMagicEffect(PITS[1].entry, 11)
	doPlayerSendTextMessage(cid, 22, DIFF_NAME[diff] .. " - Pit 1/10: " .. BOSSES[diff][1])
	doPlayerSendTextMessage(cid, 22, "Mata el boss. Palanca Next (6 min). Forfeit = salir.")
end

function svarCheckTimer(cid)
	if SvarArenaState.owner ~= cid or SvarArenaState.pitEnter == 0 then
		return true
	end
	local elapsed = os.time() - SvarArenaState.pitEnter
	if elapsed > PIT_TIME_SEC then
		doPlayerSendTextMessage(cid, 22, "Tiempo agotado (" .. PIT_TIME_SEC .. "s). Fuera.")
		doTeleportThing(cid, TEMPLE)
		doSendMagicEffect(TEMPLE, 11)
		svarResetRun()
		return false
	end
	local left = PIT_TIME_SEC - elapsed
	doPlayerSendTextMessage(cid, 22, "Tiempo restante en este pit: " .. left .. "s.")
	return true
end

function svarNext(cid)
	svarClearOwnerIfGone()

	if SvarArenaState.owner ~= cid or SvarArenaState.diff == 0 then
		doPlayerSendCancel(cid, "No tenes una corrida activa.")
		return
	end

	local pit = svarInAnyPit(cid)
	if pit == 0 or pit ~= SvarArenaState.pit then
		doPlayerSendCancel(cid, "Usa Next desde tu pit actual.")
		return
	end

	if not svarCheckTimer(cid) then
		return
	end

	local box = PITS[pit]
	-- Contar monstruos excluyendo al jugador (stackpos 253 incluye al cid)
	local monsters = 0
	local x, y
	for x = box.x0, box.x1 do
		for y = box.y0, box.y1 do
			local th = getThingfromPos({x = x, y = y, z = box.z, stackpos = 253})
			if th.itemid > 0 and th.uid ~= cid then
				monsters = monsters + 1
			end
		end
	end
	if monsters > 0 then
		doPlayerSendCancel(cid, "Aun hay " .. monsters .. " monstruo(s).")
		return
	end

	local diff = SvarArenaState.diff
	if pit >= N_PITS then
		setPlayerStorageValue(cid, STORAGE_RUN_READY, 1)
		setPlayerStorageValue(cid, STORAGE_RUN_DIFF, diff)
		SvarArenaState.pit = 0
		SvarArenaState.pitEnter = 0
		doTeleportThing(cid, REWARD_ENTRY)
		doSendMagicEffect(REWARD_ENTRY, 11)
		doPlayerSendTextMessage(cid, 22, "Victoria " .. DIFF_NAME[diff] .. "! Elegi UN cofre.")
		return
	end

	local nextPit = pit + 1
	if svarCountMonsters(PITS[nextPit]) > 0 then
		doPlayerSendCancel(cid, "Siguiente pit ocupado. Avisa a un GM.")
		return
	end
	if not svarSpawnBoss(diff, nextPit) then
		doPlayerSendCancel(cid, "No se pudo invocar el boss. Avisa a un GM.")
		return
	end

	SvarArenaState.pit = nextPit
	SvarArenaState.pitEnter = os.time()
	doTeleportThing(cid, PITS[nextPit].entry)
	doSendMagicEffect(PITS[nextPit].entry, 11)
	doPlayerSendTextMessage(
		cid,
		22,
		"Pit " .. nextPit .. "/10: " .. BOSSES[diff][nextPit]
	)
end

function svarForfeit(cid)
	if SvarArenaState.owner ~= cid then
		doPlayerSendCancel(cid, "No tenes una corrida activa.")
		return
	end
	doPlayerSendTextMessage(cid, 22, "Forfeit. Pagá de nuevo para reintentar.")
	doTeleportThing(cid, TEMPLE)
	doSendMagicEffect(TEMPLE, 11)
	setPlayerStorageValue(cid, STORAGE_RUN_READY, 0)
	svarResetRun()
end

function svarShowInfo(cid)
	doPlayerSendTextMessage(cid, 22, "Arena de Fosos - reglas")
	doPlayerSendTextMessage(cid, 22, "Greenhorn 1000gp | Scrapper 5000gp | Warlord 10000gp")
	doPlayerSendTextMessage(cid, 22, "10 pits. 1 boss cada uno. 6 min por pit.")
	doPlayerSendTextMessage(cid, 22, "Next = siguiente. Forfeit = templo.")
	doPlayerSendTextMessage(cid, 22, "Al final: 3 cofres, elegi UNO (1 vez por dificultad).")
	if SvarArenaState.owner ~= 0 then
		doPlayerSendTextMessage(cid, 22, "Ocupado: " .. SvarArenaState.ownerName)
	else
		doPlayerSendTextMessage(cid, 22, "Libre.")
	end
end

function svarChestSlot(uid)
	if uid == UID_CHEST_A then
		return 1
	end
	if uid == UID_CHEST_B then
		return 2
	end
	if uid == UID_CHEST_C then
		return 3
	end
	return 0
end

function svarOpenChest(cid, uid)
	local slot = svarChestSlot(uid)
	if slot == 0 then
		return 0
	end

	if not svarInReward(cid) then
		doPlayerSendCancel(cid, "Los cofres solo abren en la sala de premios.")
		return 1
	end

	local ready = getPlayerStorageValue(cid, STORAGE_RUN_READY)
	local diff = getPlayerStorageValue(cid, STORAGE_RUN_DIFF)
	if ready ~= 1 or diff < 1 or diff > 3 then
		doPlayerSendTextMessage(cid, 22, "It is empty.")
		return 1
	end

	local claim = CLAIM_STORAGE[diff]
	if getPlayerStorageValue(cid, claim) == 1 then
		doPlayerSendTextMessage(cid, 22, "Ya elegiste premio en " .. DIFF_NAME[diff] .. ".")
		return 1
	end

	local prize = REWARDS[diff][slot]
	doPlayerAddItem(cid, prize, 1)
	setPlayerStorageValue(cid, claim, 1)
	setPlayerStorageValue(cid, STORAGE_RUN_READY, 0)
	if SvarArenaState.owner == cid then
		svarResetRun()
	end
	doPlayerSendTextMessage(cid, 22, "You have found a " .. getItemName(prize) .. ".")
	doPlayerSendTextMessage(cid, 22, "Salida: TP sur de la sala.")
	return 1
end

function onUse(cid, item, frompos, item2, topos)
	local uid = item.uid
	if uid == UID_INFO then
		svarShowInfo(cid)
		return 1
	end
	if uid == UID_GREEN then
		svarStart(cid, 1)
		return 1
	end
	if uid == UID_SCRAP then
		svarStart(cid, 2)
		return 1
	end
	if uid == UID_WAR then
		svarStart(cid, 3)
		return 1
	end
	if uid == UID_NEXT then
		svarNext(cid)
		return 1
	end
	if uid == UID_FORFEIT then
		svarForfeit(cid)
		return 1
	end
	if uid == UID_CHEST_A or uid == UID_CHEST_B or uid == UID_CHEST_C then
		return svarOpenChest(cid, uid)
	end
	return 0
end
