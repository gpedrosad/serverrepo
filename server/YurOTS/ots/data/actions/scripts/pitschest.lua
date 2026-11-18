-- Pozos del Infierno: Cámara de las Armas (detrás del Arena de las Furias, Corazón z10).
-- Cuatro cofres con las armas traídas de 8.x; cada personaje se lleva UNA sola (storage
-- compartido 5104). La puerta de nivel 100 y las Furias del arena custodian el acceso.
-- Mapa: scripts/map/generate-inferno-pits.py pone los cofres con estos uniqueId.
-- Ver docs/items-and-map/MAPEAR_POZOS_DEL_INFIERNO.md y docs/gameplay/QUESTS.md.

local STORAGE = 5104
local PRIZES = {
	[5104] = {id = 20157, name = "Emerald Sword"},
	[5105] = {id = 20158, name = "Avenger"},
	[5106] = {id = 20159, name = "Arcane Staff"},
	[5107] = {id = 20160, name = "Arbalest"},
}

function onUse(cid, item, frompos, item2, topos)
	local prize = PRIZES[item.uid]
	if prize == nil then
		return 0
	end
	if getPlayerStorageValue(cid, STORAGE) ~= -1 then
		doPlayerSendTextMessage(cid, 22, "The forge has already granted you its gift. It is empty.")
		return 1
	end
	doPlayerSendTextMessage(cid, 22, "You have found an " .. prize.name .. ".")
	doPlayerAddItem(cid, prize.id, 1)
	setPlayerStorageValue(cid, STORAGE, 1)
	return 1
end
