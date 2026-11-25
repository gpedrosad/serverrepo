local HEAL_AMOUNT = 100
local HEAL_EFFECT = 12
local HEAL_COLOR = 30
local MSG_EVENT = 20
local COOLDOWN_STORAGE = 9120
local COOLDOWN_SECONDS = 2

function onUse(cid, item, frompos, item2, topos)
	if frompos.x ~= 65535 then
		doPlayerSendCancel(cid, "Put it inside your inventory first.")
		return 1
	end

	local now = os.time()
	local readyAt = getPlayerStorageValue(cid, COOLDOWN_STORAGE)
	if now < readyAt then
		doPlayerSendCancel(cid, "You must wait before using another field dressing.")
		return 1
	end
	if doRemoveItem(item.uid, 1) ~= 0 then
		return 0
	end
	setPlayerStorageValue(cid, COOLDOWN_STORAGE, now + COOLDOWN_SECONDS)

	local before = getPlayerHealth(cid)
	doPlayerAddHealth(cid, HEAL_AMOUNT)
	local healed = getPlayerHealth(cid) - before
	local position = getPlayerPosition(cid)
	doSendMagicEffect(position, HEAL_EFFECT)
	if healed > 0 then
		local unit = (healed == 1) and "hitpoint." or "hitpoints."
		doSendAnimatedText(position, "+" .. healed, HEAL_COLOR)
		doPlayerSendTextMessage(cid, MSG_EVENT, "You healed yourself for " .. healed .. " " .. unit)
	end
	return 1
end
