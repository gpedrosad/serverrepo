HASTE_ENCHANT_AID = 9020
SLOT_FEET = 8

BOOTS = {
	[2195] = true, -- boots of haste
	[2642] = true, -- sandals
	[2643] = true, -- leather boots
	[2644] = true, -- bunny slippers
	[2645] = true, -- steel boots
	[2646] = true, -- golden boots
	[3982] = true  -- crocodile boots
}

function onUse(cid, item, frompos, item2, topos)
	local boots = getPlayerSlotItem(cid, SLOT_FEET)

	if boots.uid == 0 or boots.uid == nil or not BOOTS[boots.itemid] then
		doPlayerSendCancel(cid, "You must wear boots to enchant them.")
		return 1
	end

	if boots.actionid == HASTE_ENCHANT_AID then
		doPlayerSendCancel(cid, "Your boots already have +20 haste.")
		return 1
	end

	doRemoveItem(item.uid, 1)
	doSetItemActionId(boots.uid, HASTE_ENCHANT_AID)
	doSendMagicEffect(getPlayerPosition(cid), 13)
	doPlayerSendTextMessage(cid, 22, "Your boots are enchanted with +20 haste.")
	doPlayerCheckFeetSpeed(cid)
	return 1
end
