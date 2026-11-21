-- Verdant Sunstone (20125): single-use boss crystal that restores full HP and mana.

local VERDANT_SUNSTONE = 20125
local STORAGE_COOLDOWN = 9115
local COOLDOWN_SEC = 60

function onUse(cid, item, frompos, item2, topos)
	if item.itemid ~= VERDANT_SUNSTONE then
		return 0
	end

	local now = os.time()
	local lastUse = getPlayerStorageValue(cid, STORAGE_COOLDOWN)
	if lastUse > 0 and (now - lastUse) < COOLDOWN_SEC then
		local wait = COOLDOWN_SEC - (now - lastUse)
		doPlayerSendTextMessage(cid, 22,
			"You must wait " .. wait .. " seconds before using another verdant sunstone.")
		doSendMagicEffect(getPlayerPosition(cid), 2)
		return 1
	end

	setPlayerStorageValue(cid, STORAGE_COOLDOWN, now)
	doPlayerAddHealth(cid, 999999)
	doPlayerAddMana(cid, 999999)
	doRemoveItem(item.uid, 1)
	doSendMagicEffect(getPlayerPosition(cid), 14)
	doPlayerSendTextMessage(cid, 22,
		"The verdant sunstone surges through you, restoring all health and mana.")
	return 1
end
