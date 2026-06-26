-- Gem imbuements: Use gem with the correct item equipped.
SLOT_FEET = 8
SLOT_ARMOR = 4
SLOT_RIGHT = 5
SLOT_LEFT = 6

WANDS = {
	[2181] = true, [2182] = true, [2183] = true, [2185] = true, [2186] = true,
	[2187] = true, [2188] = true, [2189] = true, [2190] = true, [2191] = true,
}

BOOTS = {
	[2195] = true, [2642] = true, [2643] = true, [2644] = true, [2645] = true,
	[2646] = true, [3982] = true,
}

-- Items that are not weapons but can sit in hand slots.
NOT_WEAPONS = {
	[2006] = true, [2120] = true, [2148] = true, [2152] = true, [2160] = true,
	[2260] = true, [2268] = true, [2273] = true, [2304] = true, [2311] = true,
	[2313] = true, [2389] = true, [2543] = true, [2544] = true, [2547] = true,
	[2554] = true, [1988] = true, [2512] = true,
}

IMBUE_FAIL_CHANCE = 50

function rubySpeedPercent(stacks)
	if stacks == 1 then return 5 end
	if stacks == 2 then return 9 end
	return 16
end

function rubyDelayMs(stacks)
	return math.floor(1333 * (100 - rubySpeedPercent(stacks)) / 100)
end

function isImbueWeapon(itemid)
	if not itemid or itemid == 0 then
		return false
	end
	if WANDS[itemid] or NOT_WEAPONS[itemid] then
		return false
	end
	return true
end

function getWandSlot(cid)
	local left = getPlayerSlotItem(cid, SLOT_LEFT)
	local right = getPlayerSlotItem(cid, SLOT_RIGHT)
	if right.uid and right.uid > 0 and WANDS[right.itemid] then return right end
	if left.uid and left.uid > 0 and WANDS[left.itemid] then return left end
	return nil
end

function getWeaponSlot(cid)
	local right = getPlayerSlotItem(cid, SLOT_RIGHT)
	local left = getPlayerSlotItem(cid, SLOT_LEFT)
	if right.uid and right.uid > 0 and isImbueWeapon(right.itemid) then
		return right
	end
	if left.uid and left.uid > 0 and isImbueWeapon(left.itemid) then
		return left
	end
	return nil
end

function stackAid(minAid, currentAid, maxStacks)
	if currentAid < minAid then
		return minAid
	end
	if currentAid >= minAid + maxStacks - 1 then
		return nil
	end
	return currentAid + 1
end

function rollImbueFailure(cid, gemItem)
	if math.random(1, 100) > IMBUE_FAIL_CHANCE then
		return false
	end

	doRemoveItem(gemItem.uid, 1)
	doSendMagicEffect(getPlayerPosition(cid), 2)
	doPlayerSendCancel(cid, "The imbuement failed and the gem crumbled.")
	doPlayerSendTextMessage(cid, 22, "Imbuement failed. The gem was lost.")
	return true
end

function applyImbue(cid, gemItem, target, minAid, maxStacks, msg)
	local nextAid = stackAid(minAid, target.actionid, maxStacks)
	if not nextAid then
		doPlayerSendCancel(cid, "Maximum imbuement level reached.")
		return false
	end
	if rollImbueFailure(cid, gemItem) then
		return false
	end
	doRemoveItem(gemItem.uid, 1)
	doSetItemActionId(target.uid, nextAid)
	doSendMagicEffect(getPlayerPosition(cid), 13)
	doPlayerSendTextMessage(cid, 22, msg)
	doPlayerCheckFeetSpeed(cid)
	return true
end

function onUse(cid, item, frompos, item2, topos)
	local gem = item.itemid

	if gem == 2154 then
		local boots = getPlayerSlotItem(cid, SLOT_FEET)
		if boots.uid == 0 or boots.uid == nil or not BOOTS[boots.itemid] then
			doPlayerSendCancel(cid, "Wear boots to imbue them.")
			return 1
		end
		local stacks = 0
		if boots.actionid >= 9020 and boots.actionid <= 9022 then
			stacks = boots.actionid - 9019
		end
		if stacks >= 3 then
			doPlayerSendCancel(cid, "Boots already have 3/3 haste imbuements.")
			return 1
		end
		applyImbue(cid, item, boots, 9020, 3, "Boots imbued with haste (" .. (stacks + 1) .. "/3).")
		return 1
	end

	if gem == 2153 then
		local wand = getWandSlot(cid)
		if not wand then
			doPlayerSendCancel(cid, "Equip a wand or rod to imbue it.")
			return 1
		end
		local stacks = 0
		if wand.actionid >= 9030 and wand.actionid <= 9033 then
			stacks = wand.actionid - 9029
		end
		if stacks >= 4 then
			doPlayerSendCancel(cid, "Wand already has 4/4 ML imbuements.")
			return 1
		end
		applyImbue(cid, item, wand, 9030, 4, "Wand imbued with ML (" .. (stacks + 1) .. "/4).")
		return 1
	end

	if gem == 2156 then
		local weapon = getWeaponSlot(cid)
		if not weapon then
			doPlayerSendCancel(cid, "Equip a weapon in your right or left hand to imbue it.")
			return 1
		end
		local stacks = 0
		if weapon.actionid >= 9040 and weapon.actionid <= 9042 then
			stacks = weapon.actionid - 9039
		end
		if stacks >= 3 then
			doPlayerSendCancel(cid, "This weapon already has 3/3 attack speed imbuements.")
			return 1
		end
		if weapon.actionid >= 9020 then
			if weapon.actionid >= 9040 and weapon.actionid <= 9042 then
				-- allowed: ruby stacks on same weapon
			else
			doPlayerSendCancel(cid, "That item already has another imbuement.")
			return 1
			end
		end
		if rollImbueFailure(cid, item) then
			return 1
		end
		doRemoveItem(item.uid, 1)
		doSetItemActionId(weapon.uid, 9040 + stacks)
		doSendMagicEffect(getPlayerPosition(cid), 13)
		doPlayerSendTextMessage(cid, 22, "Weapon imbued with attack speed (" .. (stacks + 1) .. "/3): +" .. rubySpeedPercent(stacks + 1) .. "% (" .. rubyDelayMs(stacks + 1) .. "ms per hit).")
		doPlayerCheckFeetSpeed(cid)
		return 1
	end

	if gem == 2155 then
		local armor = getPlayerSlotItem(cid, SLOT_ARMOR)
		if armor.uid == 0 or armor.uid == nil then
			doPlayerSendCancel(cid, "Wear armor to imbue it.")
			return 1
		end
		if armor.actionid == 9050 or armor.actionid == 9041 then
			doPlayerSendCancel(cid, "Armor already has skill imbuement.")
			return 1
		end
		if armor.actionid >= 9020 then
			doPlayerSendCancel(cid, "That item already has another imbuement.")
			return 1
		end
		if rollImbueFailure(cid, item) then
			return 1
		end
		doRemoveItem(item.uid, 1)
		doSetItemActionId(armor.uid, 9050)
		doSendMagicEffect(getPlayerPosition(cid), 13)
		doPlayerSendTextMessage(cid, 22, "Armor imbued with +3 attack skills (Paladin/Knight).")
		doPlayerCheckFeetSpeed(cid)
		return 1
	end

	doPlayerSendCancel(cid, "This gem cannot be used for imbuements.")
	return 1
end
