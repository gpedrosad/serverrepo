-- Gem imbuements: Use gem with the correct item equipped.
SLOT_FEET = 8
SLOT_ARMOR = 4
SLOT_RIGHT = 5
SLOT_LEFT = 6

WANDS = {
	[2181] = true, [2182] = true, [2183] = true, [2185] = true, [2186] = true,
	[2187] = true, [2188] = true, [2189] = true, [2190] = true, [2191] = true,
	[20123] = true, -- Crimson Wand (Violet Gem ML). Train Wand 20126 excluded on purpose.
}

BOOTS = {
	[2195] = true, [2642] = true, [2643] = true, [2644] = true, [2645] = true,
	[2646] = true, [3982] = true, [20129] = true,
}

-- Items that are not weapons but can sit in hand slots.
-- Big Ruby must never target shields/torches/ammo/tools: the gem would be
-- consumed and the actionid written, but C++ only applies ruby speed to real
-- weapons (isRubyImbueWeaponItem excludes SHIELD and requires isWeapon()).
NOT_WEAPONS = {
	-- ammo, runes, tools, containers, coins
	[2006] = true, [2120] = true, [2148] = true, [2152] = true, [2160] = true,
	[2260] = true, [2268] = true, [2273] = true, [2304] = true, [2311] = true,
	[2313] = true, [2389] = true, [2543] = true, [2544] = true, [2547] = true,
	[2554] = true, [1988] = true,
	-- shields 7.6 (2509-2542) + newer standard shields (3973-3975)
	[2509] = true, [2510] = true, [2511] = true, [2512] = true, [2513] = true,
	[2514] = true, [2515] = true, [2516] = true, [2517] = true, [2518] = true,
	[2519] = true, [2520] = true, [2521] = true, [2522] = true, [2523] = true,
	[2524] = true, [2525] = true, [2526] = true, [2527] = true, [2528] = true,
	[2529] = true, [2530] = true, [2531] = true, [2532] = true, [2533] = true,
	[2534] = true, [2535] = true, [2536] = true, [2537] = true, [2538] = true,
	[2539] = true, [2540] = true, [2541] = true, [2542] = true,
	[3973] = true, [3974] = true, [3975] = true,
	-- Zagan/custom shields present in items-zagan-test.otb (weaponType SHIELD)
	[20101] = true, [20128] = true, [20149] = true, [20150] = true,
	[20151] = true, [20153] = true,
	-- hand-held light sources/tools (equippable, but weaponType NONE)
	[2050] = true, [2051] = true, [2052] = true, [2053] = true, [2054] = true,
	[2055] = true, [2056] = true, [2057] = true,
	[2580] = true, [2581] = true, [2582] = true, [2583] = true, [2584] = true,
	[2585] = true, [2586] = true, [2587] = true, [2588] = true,
	-- decorative/non-functional crystal wand (not in WANDS)
	[2184] = true,
}

IMBUE_FAIL_CHANCE = 50
NIGHTGLASS_DAGGER = 20137
NIGHTGLASS_SPEED_AID = 9060
NIGHTGLASS_MAX_STACKS = 5
CRYSTAL_ARROW = 2352
CRYSTAL_ARROW_SPEED_AID = 9070
CRYSTAL_ARROW_MAX_STACKS = 5
BLUE_GEM = 2158

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
	if itemid == 20126 then -- Train Wand: no gem imbues
		return false
	end
	if itemid == CRYSTAL_ARROW then
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

function nightglassSuccessPercent(currentStacks)
	return 90 - (currentStacks * 10)
end

function rollNightglassImbueFailure(cid, gemItem, currentStacks)
	local successPct = nightglassSuccessPercent(currentStacks)
	if math.random(1, 100) <= successPct then
		return false
	end

	doRemoveItem(gemItem.uid, 1)
	doSendMagicEffect(getPlayerPosition(cid), 2)
	doPlayerSendCancel(cid, "The nightglass imbuement failed and the gem crumbled.")
	doPlayerSendTextMessage(cid, 22, "Imbuement failed (" .. successPct .. "% chance). The gem was lost.")
	return true
end

function nightglassSpeedPercent(stacks)
	return stacks * 5
end

function nightglassDelayMs(stacks)
	return math.floor(1333 * (100 - nightglassSpeedPercent(stacks)) / 100)
end

function crystalArrowSpeedPercent(stacks)
	return stacks * 5
end

function crystalArrowDelayMs(stacks)
	return math.floor(1333 * (100 - crystalArrowSpeedPercent(stacks)) / 100)
end

function getCrystalArrowSlot(cid)
	local right = getPlayerSlotItem(cid, SLOT_RIGHT)
	local left = getPlayerSlotItem(cid, SLOT_LEFT)
	if right.uid and right.uid > 0 and right.itemid == CRYSTAL_ARROW then
		return right
	end
	if left.uid and left.uid > 0 and left.itemid == CRYSTAL_ARROW then
		return left
	end
	return nil
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

local MEMORY_GEM = 20664
-- Item::setActionId clamps values below 100. This value carries no imbuement.
local MEMORY_CLEAR_AID = 100
local HANDS = {SLOT_RIGHT, SLOT_LEFT}
local MEMORY_RULES = {
	boots = {aid = 9020, max = 3, slots = {SLOT_FEET}},
	wand = {aid = 9030, max = 4, slots = HANDS},
	ruby = {aid = 9040, max = 3, slots = HANDS},
	armor = {aid = 9050, max = 4, slots = {SLOT_ARMOR}},
	nightglass = {aid = NIGHTGLASS_SPEED_AID, max = NIGHTGLASS_MAX_STACKS, slots = HANDS},
	arrow = {aid = CRYSTAL_ARROW_SPEED_AID, max = CRYSTAL_ARROW_MAX_STACKS, slots = HANDS},
}
local memoryEquipment

local function memoryFamily(itemid)
	if BOOTS[itemid] then return "boots" end
	if WANDS[itemid] then return "wand" end
	if itemid == NIGHTGLASS_DAGGER then return "nightglass" end
	if itemid == CRYSTAL_ARROW then return "arrow" end
	if not memoryEquipment then
		memoryEquipment = dofile("data/actions/lib/memory_gem_equipment.lua")
	end
	if memoryEquipment.armor[itemid] then return "armor" end
	if memoryEquipment.ruby[itemid] then return "ruby" end
end

local function memoryCap(rule, itemid)
	if rule == MEMORY_RULES.armor and itemid == 2494 then return 6 end
	return rule.max
end

local function memoryStacks(rule, item)
	if rule == MEMORY_RULES.armor and item.actionid == 9041 then return 3 end
	local stacks = item.actionid - rule.aid + 1
	if stacks >= 1 and stacks <= memoryCap(rule, item.itemid) then return stacks end
	return 0
end

local function rejectMemory(cid, message)
	doPlayerSendCancel(cid, message)
	return 1
end

local function transferMemory(cid, gem, frompos, target, topos)
	if not target or target.uid == 0 then
		return rejectMemory(cid, "Equip the imbued item and use the memory gem on the new gear.")
	end
	if frompos.x ~= 65535 or topos.x ~= 65535 then
		return rejectMemory(cid, "Carry the memory gem and the destination item in your inventory.")
	end
	local family = memoryFamily(target.itemid)
	if not family or (target.actionid ~= 0 and target.actionid ~= MEMORY_CLEAR_AID) then
		return rejectMemory(cid, "Choose compatible gear with no existing enchantment.")
	end

	local rule = MEMORY_RULES[family]
	local source, stacks
	for _, slot in ipairs(rule.slots) do
		local equipped = getPlayerSlotItem(cid, slot)
		if equipped.uid > 0 and equipped.uid ~= target.uid and memoryFamily(equipped.itemid) == family then
			local levels = memoryStacks(rule, equipped)
			if levels >= 2 then
				if source then
					return rejectMemory(cid, "Equip only one matching imbued item as the source.")
				end
				source, stacks = equipped, levels
			end
		end
	end
	if not source then
		return rejectMemory(cid, "Equip compatible gear with at least two imbuement levels.")
	end
	local transferred = stacks - 1
	local cap = memoryCap(rule, target.itemid)
	if transferred > cap then
		return rejectMemory(cid, "The destination cannot hold all of the transferred levels.")
	end

	if doSetItemActionId(source.uid, MEMORY_CLEAR_AID) ~= 0 then
		return rejectMemory(cid, "The memory gem could not read the source item.")
	end
	if doSetItemActionId(target.uid, rule.aid + transferred - 1) ~= 0 then
		doSetItemActionId(source.uid, source.actionid)
		return rejectMemory(cid, "The memory gem could not imbue the destination.")
	end
	if doRemoveItem(gem.uid, 1) ~= 0 then
		doSetItemActionId(target.uid, target.actionid)
		doSetItemActionId(source.uid, source.actionid)
		return rejectMemory(cid, "The memory gem could not complete the transfer.")
	end
	doPlayerCheckFeetSpeed(cid)
	doSendMagicEffect(getPlayerPosition(cid), 13)
	doPlayerSendTextMessage(cid, 22, "The memory gem transferred " .. transferred .. "/" .. cap ..
		" imbuement levels. The source item is now clean.")
	return 1
end

function onUse(cid, item, frompos, item2, topos)
	local gem = item.itemid

	if gem == MEMORY_GEM then
		return transferMemory(cid, item, frompos, item2, topos)
	end

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

		if weapon.itemid == 20211 or weapon.itemid == 20212 or weapon.itemid == 20213 then
			doPlayerSendCancel(cid, "These stars already have a fixed enchantment and cannot be imbued.")
			return 1
		end

		if weapon.itemid == 20250 or weapon.itemid == 20251 or weapon.itemid == 20252 then
			doPlayerSendCancel(cid, "These relics already have a fixed enchantment and cannot be imbued.")
			return 1
		end

		if weapon.itemid == 20660 then
			doPlayerSendCancel(cid, "The quicksilver katana already has a fixed enchantment and cannot be imbued.")
			return 1
		end

		if weapon.itemid == NIGHTGLASS_DAGGER then
			local stacks = 0
			if weapon.actionid >= NIGHTGLASS_SPEED_AID and weapon.actionid <= NIGHTGLASS_SPEED_AID + NIGHTGLASS_MAX_STACKS - 1 then
				stacks = weapon.actionid - NIGHTGLASS_SPEED_AID + 1
			end
			if stacks >= NIGHTGLASS_MAX_STACKS then
				doPlayerSendCancel(cid, "Nightglass dagger already has 5/5 speed imbuements.")
				return 1
			end
			local isNightglassAid = weapon.actionid >= NIGHTGLASS_SPEED_AID and
				weapon.actionid <= NIGHTGLASS_SPEED_AID + NIGHTGLASS_MAX_STACKS - 1
			if weapon.actionid >= 9020 and not isNightglassAid and weapon.actionid ~= 9041 and
				((weapon.actionid >= 9040 and weapon.actionid <= 9042) == false) then
				doPlayerSendCancel(cid, "That item already has another imbuement.")
				return 1
			end
			if rollNightglassImbueFailure(cid, item, stacks) then
				return 1
			end
			doRemoveItem(item.uid, 1)
			doSetItemActionId(weapon.uid, NIGHTGLASS_SPEED_AID + stacks)
			doSendMagicEffect(getPlayerPosition(cid), 13)
			local nextStacks = stacks + 1
			doPlayerSendTextMessage(cid, 22, "Nightglass dagger imbued with speed (" .. nextStacks .. "/5): +" ..
				nightglassSpeedPercent(nextStacks) .. "% (" .. nightglassDelayMs(nextStacks) .. "ms per hit).")
			doPlayerCheckFeetSpeed(cid)
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
		-- Demon armor (2494): hasta 6 stacks (AID 9050–9055). Otras armaduras: 4 (9050–9053).
		local DEMON_ARMOR = 2494
		local maxStacks = 4
		if armor.itemid == DEMON_ARMOR then
			maxStacks = 6
		end
		local stacks = 0
		if armor.actionid >= 9050 and armor.actionid <= 9055 then
			stacks = armor.actionid - 9049
		elseif armor.actionid == 9041 then
			stacks = 3
		end
		if stacks >= maxStacks then
			doPlayerSendCancel(cid, "Armor already has " .. maxStacks .. "/" .. maxStacks .. " skill imbuements.")
			return 1
		end
		if armor.actionid >= 9020 and armor.actionid <= 9042 and armor.actionid ~= 9041 then
			doPlayerSendCancel(cid, "That item already has another imbuement.")
			return 1
		end
		if rollImbueFailure(cid, item) then
			return 1
		end
		doRemoveItem(item.uid, 1)
		doSetItemActionId(armor.uid, 9050 + stacks)
		doSendMagicEffect(getPlayerPosition(cid), 13)
		doPlayerSendTextMessage(cid, 22, "Armor imbued with skills (" .. (stacks + 1) .. "/" .. maxStacks .. "). +1 sword/club/axe/dist per stack.")
		doPlayerCheckFeetSpeed(cid)
		return 1
	end

	if gem == BLUE_GEM then
		local arrow = getCrystalArrowSlot(cid)
		if not arrow then
			doPlayerSendCancel(cid, "Equip a crystal arrow to imbue it.")
			return 1
		end
		local stacks = 0
		if arrow.actionid >= CRYSTAL_ARROW_SPEED_AID and
			arrow.actionid <= CRYSTAL_ARROW_SPEED_AID + CRYSTAL_ARROW_MAX_STACKS - 1 then
			stacks = arrow.actionid - CRYSTAL_ARROW_SPEED_AID + 1
		end
		if stacks >= CRYSTAL_ARROW_MAX_STACKS then
			doPlayerSendCancel(cid, "Crystal arrow already has 5/5 speed imbuements.")
			return 1
		end
		local isCrystalAid = arrow.actionid >= CRYSTAL_ARROW_SPEED_AID and
			arrow.actionid <= CRYSTAL_ARROW_SPEED_AID + CRYSTAL_ARROW_MAX_STACKS - 1
		if arrow.actionid >= 9020 and not isCrystalAid then
			doPlayerSendCancel(cid, "That item already has another imbuement.")
			return 1
		end
		if rollImbueFailure(cid, item) then
			return 1
		end
		doRemoveItem(item.uid, 1)
		doSetItemActionId(arrow.uid, CRYSTAL_ARROW_SPEED_AID + stacks)
		doSendMagicEffect(getPlayerPosition(cid), 13)
		local nextStacks = stacks + 1
		doPlayerSendTextMessage(cid, 22, "Crystal arrow imbued with speed (" .. nextStacks .. "/5): +" ..
			crystalArrowSpeedPercent(nextStacks) .. "% (" .. crystalArrowDelayMs(nextStacks) .. "ms per hit).")
		doPlayerCheckFeetSpeed(cid)
		return 1
	end

	doPlayerSendCancel(cid, "This gem cannot be used for imbuements.")
	return 1
end
