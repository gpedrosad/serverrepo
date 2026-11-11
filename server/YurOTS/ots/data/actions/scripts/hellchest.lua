-- Hell Quest: Cámara de la Elección (detrás del Ashen Lord, Abismo z9).
-- Cuatro cofres; cada personaje se lleva UNO solo (storage compartido 5100).
-- Mapa: scripts/map/generate-hell-quest.py pone los cofres con estos uniqueId.
-- Ver docs/gameplay/HELL_QUEST.md.

local STORAGE = 5100
local PRIZES = {
	[5100] = {id = 2493, name = "Demon Helmet"},
	[5101] = {id = 2472, name = "Magic Plate Armor"},
	[5102] = {id = 2195, name = "Boots of Haste"},
	[5103] = {id = 2520, name = "Demon Shield"},
}

function onUse(cid, item, frompos, item2, topos)
	local prize = PRIZES[item.uid]
	if prize == nil then
		return 0
	end
	if getPlayerStorageValue(cid, STORAGE) ~= -1 then
		doPlayerSendTextMessage(cid, 22, "The fire has already granted you its gift. It is empty.")
		return 1
	end
	doPlayerSendTextMessage(cid, 22, "You have found a " .. prize.name .. ".")
	doPlayerAddItem(cid, prize.id, 1)
	setPlayerStorageValue(cid, STORAGE, 1)
	return 1
end
