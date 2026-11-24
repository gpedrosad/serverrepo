-- El Crisol v4: palancas 7200 Bronze / 7201 Silver / 7202 Gold / 7203 Info.
-- Ver docs/gameplay/CRUCIBLE.md. Textos ASCII (cliente 7.6).
--
-- La palanca solo valida y manda al grupo a la arena con un pase (storage). La pelea la corre
-- el guardián Varkon (data/npc/scripts/crucible_warden.lua): cuenta regresiva, spawn del elite y su
-- escolta, contador en pantalla, premio diario, vuelta a la sala y limpieza de arenas abandonadas.
--
--   * Escalera diaria: Silver pide Bronze limpio hoy; Gold pide Silver limpio hoy y no haber
--     matado al jefe de Oro hoy.
--   * Entran el que tira y los jugadores parados en la plataforma 3x2 de esa puerta que cumplan,
--     hasta tantos como puntos de llegada tenga la arena.
--   * Una arena está libre si no hay jugadores ni monstruos (Varkon la vacía en ~3 s).

dofile("data/actions/lib/crucible.lua")

UID_INFO = 7203
DOORS = {[7200] = "bronze", [7201] = "silver", [7202] = "gold"}
LEVER_LEFT, LEVER_RIGHT = 1945, 1946

MSG_INFO = 22
EFFECT_TELEPORT = 11
EFFECT_PUFF = 2

-------------------------------------------------------------------- utilidades

-- {players = {uid...}, monsters = n}: criaturas dentro de una caja.
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

local function inHub(uid)
	local pos = getPlayerPosition(uid)
	return pos ~= nil and crucibleInBox(pos.x, pos.y, pos.z, CRUCIBLE.hub)
end

-- El que tira + los de la plataforma que cumplan, hasta `max`. Devuelve grupo y {uid, motivo} de los que quedan.
local function padGroup(cid, door, max)
	local group, left = {cid}, {}
	local seen = {[getPlayerName(cid)] = true}
	for _, uid in ipairs(scan(CRUCIBLE.pads[door]).players) do
		local name = getPlayerName(uid)
		if name and not seen[name] then
			seen[name] = true
			local err = crucibleEntryError(uid, door)
			if err then
				table.insert(left, {uid, "You stay behind: " .. err})
			elseif table.getn(group) < max then
				table.insert(group, uid)
			else
				table.insert(left, {uid, "Group full (max " .. max .. "). Wait for the next run."})
			end
		end
	end
	return group, left
end

local function flipLever(item)
	if item.itemid == LEVER_LEFT then
		doTransformItem(item.uid, LEVER_RIGHT)
	elseif item.itemid == LEVER_RIGHT then
		doTransformItem(item.uid, LEVER_LEFT)
	end
end

-------------------------------------------------------------------- palancas

local function startDoor(cid, item, door)
	local tier = CRUCIBLE.tiers[door]
	if not inHub(cid) then
		doPlayerSendCancel(cid, "Use the lever from the Crucible Hall.")
		return
	end

	local err = crucibleEntryError(cid, door)
	if err then
		doPlayerSendCancel(cid, "Sorry, " .. err)
		return
	end

	local arena = CRUCIBLE.arenas[door]
	local inside = scan(arena)
	if table.getn(inside.players) > 0 then
		doPlayerSendCancel(cid, "The " .. tier.label .. " arena is busy: " .. names(inside.players) .. " is fighting.")
		return
	end
	if inside.monsters > 0 then
		doPlayerSendCancel(cid, "Varkon is still clearing the " .. tier.label .. " arena. Try again in a few seconds.")
		return
	end

	local group, left = padGroup(cid, door, table.getn(arena.arrivals))
	for i, uid in ipairs(group) do
		crucibleGiveTicket(uid, door)
		doSendMagicEffect(getPlayerPosition(uid), EFFECT_PUFF)
		doTeleportThing(uid, arena.arrivals[i])
		doSendMagicEffect(arena.arrivals[i], EFFECT_TELEPORT)
		doPlayerSendTextMessage(uid, MSG_INFO, "Crucible " .. tier.label .. " gate: " .. arena.name
			.. ". Kill every monster to clear it. Exit: the southern portal.")
	end
	flipLever(item)

	if table.getn(group) > 1 then
		doPlayerSendTextMessage(cid, MSG_INFO, "Group: " .. names(group) .. ".")
	end
	for _, entry in ipairs(left) do
		doPlayerSendCancel(entry[1], entry[2])
	end
end

local function arenaState(door)
	local s = scan(CRUCIBLE.arenas[door])
	if table.getn(s.players) > 0 then
		return "busy (" .. names(s.players) .. ")"
	elseif s.monsters > 0 then
		return "being reset"
	end
	return "free"
end

local function showInfo(cid)
	doPlayerSendTextMessage(cid, MSG_INFO, "The Crucible: clear Bronze, then Silver, then Gold. "
		.. "Each gate gives its reward once per day; the Gold boss can be defeated once per day.")
	doPlayerSendTextMessage(cid, MSG_INFO, crucibleLineupText())
	doPlayerSendTextMessage(cid, MSG_INFO, "Your progress today: " .. crucibleProgressText(cid))
	local states = {}
	for _, door in ipairs(CRUCIBLE.order) do
		table.insert(states, CRUCIBLE.tiers[door].label .. " " .. arenaState(door))
	end
	doPlayerSendTextMessage(cid, MSG_INFO, "Arenas: " .. table.concat(states, ", ") .. ".")
end

function onUse(cid, item, frompos, item2, topos)
	if item.uid == UID_INFO then
		showInfo(cid)
		flipLever(item)
		return 1
	end
	local door = DOORS[item.uid]
	if door then
		startDoor(cid, item, door)
		return 1
	end
	return 0
end
