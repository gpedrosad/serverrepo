-- El Crisol: palancas 7200 Bronce / 7201 Plata / 7202 Oro / 7203 Info.
-- Bosses diarios (rotacion por dia del anio % 7). Textos ASCII (cliente 7.6).

UID_BRONZE = 7200
UID_SILVER = 7201
UID_GOLD = 7202
UID_INFO = 7203

ARENAS = {
	bronze = {
		x0 = 111, y0 = 81, x1 = 121, y1 = 91, z = 0,
		entry = {x = 116, y = 86, z = 0},
	},
	silver = {
		x0 = 141, y0 = 81, x1 = 153, y1 = 95, z = 0,
		entry = {x = 147, y = 88, z = 0},
	},
	gold = {
		x0 = 171, y0 = 81, x1 = 187, y1 = 99, z = 0,
		entry = {x = 179, y = 90, z = 0},
	},
}

HUB = {x0 = 81, y0 = 81, x1 = 99, y1 = 95, z = 0}

-- Por dia: elite bronce, elite plata, boss oro (custom), rare exclusivo
DAILY = {
	{"Minotaur Guard", "Beholder", "Crucible Ashlord", "ashlord emberblade"},
	{"Cyclops", "Demon Skeleton", "Crucible Frostwarden", "frostwarden chillblade"},
	{"Dwarf Guard", "Vampire", "Crucible Bonepriest", "bonepriest reaver"},
	{"Minotaur Mage", "Hero", "Crucible Ironhide", "ironhide crusher"},
	{"Beholder", "Dragon", "Crucible Venomqueen", "venomqueen fang"},
	{"Giant Spider", "Black Knight", "Crucible Stormcaller", "stormcaller maul"},
	{"Vampire", "Warlock", "Crucible Bloodreaver", "bloodreaver saber"},
}

PACKS = {
	bronze = {"Minotaur", "Minotaur Archer", "Minotaur Guard"},
	silver = {"Demon Skeleton", "Ghoul", "Beholder", "Stalker"},
	gold = {"Dragon", "Giant Spider", "Hero", "Necromancer"},
}

PACK_COUNT = {bronze = 3, silver = 4, gold = 5}

if not CrucibleState then
	CrucibleState = {
		door = "",
		owner = 0,
		ownerName = "",
		day = -1,
	}
end

function crucibleDayIndex()
	local day = tonumber(os.date("%j"))
	if not day then
		day = 1
	end
	return ((day - 1) % table.getn(DAILY)) + 1
end

function crucibleToday()
	return DAILY[crucibleDayIndex()]
end

function crucibleDoorName(uid)
	if uid == UID_BRONZE then
		return "bronze"
	end
	if uid == UID_SILVER then
		return "silver"
	end
	if uid == UID_GOLD then
		return "gold"
	end
	return nil
end

function crucibleInBox(pos, box)
	return pos.z == box.z
		and pos.x >= box.x0 and pos.x <= box.x1
		and pos.y >= box.y0 and pos.y <= box.y1
end

function crucibleInHub(cid)
	local pos = getPlayerPosition(cid)
	if not pos then
		return false
	end
	return crucibleInBox(pos, HUB)
end

function crucibleInAnyArena(cid)
	local pos = getPlayerPosition(cid)
	if not pos then
		return false
	end
	for _, box in pairs(ARENAS) do
		if crucibleInBox(pos, box) then
			return true
		end
	end
	return false
end

function crucibleCountMonsters(box)
	local count = 0
	for x = box.x0, box.x1 do
		for y = box.y0, box.y1 do
			local pos = {x = x, y = y, z = box.z, stackpos = 253}
			local th = getThingfromPos(pos)
			if th.itemid > 0 then
				count = count + 1
			end
		end
	end
	return count
end

function crucibleClearOwnerIfGone()
	if CrucibleState.owner == 0 then
		return
	end
	if not crucibleInHub(CrucibleState.owner) and not crucibleInAnyArena(CrucibleState.owner) then
		CrucibleState.door = ""
		CrucibleState.owner = 0
		CrucibleState.ownerName = ""
	end
end

function crucibleSpawnAt(name, pos)
	local summoned = doSummonCreature(name, pos)
	return summoned ~= 0
end

function crucibleSpawnOffsets(box, n)
	local cx = math.floor((box.x0 + box.x1) / 2)
	local cy = math.floor((box.y0 + box.y1) / 2)
	local spots = {
		{0, 0}, {1, 0}, {-1, 0}, {0, 1}, {0, -1},
		{1, 1}, {-1, 1}, {1, -1}, {-1, -1}, {2, 0},
		{-2, 0}, {0, 2},
	}
	local out = {}
	for i = 1, n do
		local s = spots[((i - 1) % table.getn(spots)) + 1]
		local x = cx + s[1]
		local y = cy + s[2]
		if x < box.x0 + 1 then x = box.x0 + 1 end
		if x > box.x1 - 1 then x = box.x1 - 1 end
		if y < box.y0 + 1 then y = box.y0 + 1 end
		if y > box.y1 - 1 then y = box.y1 - 1 end
		table.insert(out, {x = x, y = y, z = box.z})
	end
	return out
end

function crucibleStartDoor(cid, door)
	crucibleClearOwnerIfGone()

	if not crucibleInHub(cid) then
		doPlayerSendCancel(cid, "Usa la palanca desde el hub del Crisol.")
		return
	end

	if CrucibleState.door ~= "" and CrucibleState.owner ~= 0 and CrucibleState.owner ~= cid then
		if crucibleInHub(CrucibleState.owner) or crucibleInAnyArena(CrucibleState.owner) then
			doPlayerSendCancel(cid, "Corrida activa de " .. CrucibleState.ownerName .. ".")
			return
		end
	end

	-- Misma puerta: si limpio, permitir re-entrar; si hay mobs, bloquear
	local box = ARENAS[door]
	local left = crucibleCountMonsters(box)
	if CrucibleState.door == door and CrucibleState.owner == cid and left > 0 then
		doPlayerSendCancel(cid, "Aun hay " .. left .. " monstruo(s) en tu arena.")
		return
	end

	-- Otra puerta sellada mientras haya mobs o corrida propia incompleta
	if CrucibleState.door ~= "" and CrucibleState.door ~= door and CrucibleState.owner == cid then
		local old = ARENAS[CrucibleState.door]
		if crucibleCountMonsters(old) > 0 then
			doPlayerSendCancel(cid, "Puerta sellada. Limpia " .. CrucibleState.door .. " o sali por el TP.")
			return
		end
	end

	local today = crucibleToday()
	local elite
	if door == "bronze" then
		elite = today[1]
	elseif door == "silver" then
		elite = today[2]
	else
		elite = today[3]
	end

	local pack = PACKS[door]
	local n = PACK_COUNT[door]
	local spots = crucibleSpawnOffsets(box, n + 1)
	local ok = 0
	for i = 1, n do
		local name = pack[((i - 1) % table.getn(pack)) + 1]
		if crucibleSpawnAt(name, spots[i]) then
			ok = ok + 1
		end
	end
	if crucibleSpawnAt(elite, spots[n + 1]) then
		ok = ok + 1
	end

	if ok < 1 then
		doPlayerSendCancel(cid, "No se pudieron invocar monstruos. Avisa a un GM.")
		return
	end

	CrucibleState.door = door
	CrucibleState.owner = cid
	CrucibleState.ownerName = getPlayerName(cid)
	CrucibleState.day = crucibleDayIndex()

	doTeleportThing(cid, box.entry)
	doSendMagicEffect(box.entry, 11)
	doPlayerSendTextMessage(
		cid,
		22,
		"Crisol " .. door .. ": elite de hoy = " .. elite .. ". Mata todo o sali por el TP sur."
	)
end

function crucibleShowInfo(cid)
	local today = crucibleToday()
	local day = crucibleDayIndex()
	doPlayerSendTextMessage(cid, 22, "Crisol - bosses de hoy (dia #" .. day .. ")")
	doPlayerSendTextMessage(cid, 22, "Bronce: " .. today[1])
	doPlayerSendTextMessage(cid, 22, "Plata: " .. today[2])
	doPlayerSendTextMessage(cid, 22, "Oro: " .. today[3])
	doPlayerSendTextMessage(cid, 22, "Rare del dia (solo Oro): " .. today[4])
	doPlayerSendTextMessage(cid, 22, "Elegi una palanca. La puerta se sella hasta limpiar o salir.")
end

function onUse(cid, item, frompos, item2, topos)
	if item.uid == UID_INFO then
		crucibleShowInfo(cid)
		return 1
	end
	local door = crucibleDoorName(item.uid)
	if door then
		crucibleStartDoor(cid, door)
		return 1
	end
	return 0
end
