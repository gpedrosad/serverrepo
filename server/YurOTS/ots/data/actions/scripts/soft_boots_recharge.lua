-- Azure Sunstone (20124): recharges worn soft boots (3550 -> 3549, 4h duration).
-- Boss-only drop; does not overlap with premium runes (20131/20132).

local AZURE_SUNSTONE = 20124
local WORN_SOFT_BOOTS = 3550
local SOFT_BOOTS = 3549

function onUse(cid, item, frompos, item2, topos)
	if item.itemid ~= AZURE_SUNSTONE then
		return 0
	end

	-- Support both "Use With" directly on worn soft boots and simple right-click "Use".
	if item2 and item2.itemid == WORN_SOFT_BOOTS and item2.uid and item2.uid > 0 then
		doTransformItem(item2.uid, SOFT_BOOTS)
		doRemoveItem(item.uid, 1)
		doSendMagicEffect(getPlayerPosition(cid), 12)
		doPlayerSendTextMessage(cid, 22,
			"The azure sunstone restores your soft boots to full power (4 hours).")
		return 1
	end

	if doPlayerRemoveItem(cid, WORN_SOFT_BOOTS, 1) == 1 then
		doPlayerAddItem(cid, SOFT_BOOTS, 1)
		doRemoveItem(item.uid, 1)
		doSendMagicEffect(getPlayerPosition(cid), 12)
		doPlayerSendTextMessage(cid, 22,
			"The azure sunstone restores your soft boots to full power (4 hours).")
		return 1
	end

	doPlayerSendTextMessage(cid, 22,
		"Carry worn soft boots in your backpack or use this crystal directly on them to recharge.")
	doSendMagicEffect(getPlayerPosition(cid), 2)
	return 1
end
