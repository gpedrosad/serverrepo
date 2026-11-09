-- Dark Rodo (runas, backpacks de runas, fluidos, wands y rods).
RUNE_BUYS = {
	{keys = {'sudden death', 'sd'}, itemid = 2268, unitPrice = 250, runeCharges = 1},
	{keys = {'ultimate healing', 'uh'}, itemid = 2273, unitPrice = 200, runeCharges = 2},
	{keys = {'great fireball', 'gfb'}, itemid = 2304, unitPrice = 45, runeCharges = 3},
	{keys = {'explosion'}, itemid = 2313, unitPrice = 35, runeCharges = 3},
	{keys = {'heavy magic missile', 'hmm'}, itemid = 2311, unitPrice = 15, runeCharges = 5},
	{keys = {'blank rune', 'blank'}, itemid = 2260, unitPrice = 10, itemQuantity = true},
	{keys = {'strong mana potion', 'strong mana', 'smp'}, itemid = 2006, fluidSubtype = 14, unitPrice = 250},
	{keys = {'manafluid', 'mana fluid', 'mana'}, itemid = 2006, fluidSubtype = 7, unitPrice = 100},
}

WAND_BUYS = {
	{keys = {'cosmic energy'}, itemid = 2189, unitPrice = 10000},
	{keys = {'dragonbreath'}, itemid = 2191, unitPrice = 1000},
	{keys = {'inferno'}, itemid = 2187, unitPrice = 15000},
	{keys = {'moonlight'}, itemid = 2186, unitPrice = 1000},
	{keys = {'plague'}, itemid = 2188, unitPrice = 5000},
	{keys = {'quagmire'}, itemid = 2181, unitPrice = 10000},
	{keys = {'snakebite'}, itemid = 2182, unitPrice = 500},
	{keys = {'tempest'}, itemid = 2183, unitPrice = 15000},
	{keys = {'volcanic'}, itemid = 2185, unitPrice = 5000},
	{keys = {'vortex'}, itemid = 2190, unitPrice = 500},
}

BP_RUNES = 20       -- runas por mochila

-- Una mochila cuesta lo mismo que 20 runas sueltas; la mochila va de regalo para que el precio
-- sea redondo (antes multiplicaba además por las cargas: la bp de UH salía 8000 y 20 UH 4000).
local function backpackPrice(entry)
	return entry.unitPrice * BP_RUNES
end

local function backpackSummary()
	local parts = {}
	for i = 1, table.getn(RUNE_BUYS) do
		local e = RUNE_BUYS[i]
		if e.runeCharges ~= nil or e.itemQuantity ~= nil then
			table.insert(parts, 'bp ' .. e.keys[table.getn(e.keys)] .. ' ' .. npcFormatPrice(backpackPrice(e)))
		end
	end
	return table.concat(parts, ', ')
end

RUNES_BACKPACKS = 'Rune backpacks (' .. BP_RUNES .. ' runes + backpack): ' .. backpackSummary() .. '.'
RUNES_HELP = 'Runes: HMM 15gp, UH 200gp, GFB 45gp, explosion 35gp, SD 250gp, blank 10gp. Say any amount, e.g. "3 sd" or "10 uh". '
	.. RUNES_BACKPACKS .. ' Mana fluid 100gp, strong mana potion (SMP) 250gp. Say "wands" or "rods" for magic weapons.'

local function summarizeCatalog(entries, groupName)
	local parts = {groupName .. ':'}
	for i = 1, table.getn(entries) do
		local entry = entries[i]
		parts[#parts + 1] = entry.keys[1] .. ' ' .. npcFormatPrice(entry.unitPrice)
	end
	return table.concat(parts, ', ')
end

local function matchBackpack(msg)
	local prefixes = {'bp of ', 'backpack of ', 'bp ', 'backpack '}
	for i = 1, table.getn(RUNE_BUYS) do
		local entry = RUNE_BUYS[i]
		if entry.runeCharges ~= nil or entry.itemQuantity ~= nil then
			for p = 1, table.getn(prefixes) do
				for k = 1, table.getn(entry.keys) do
					if msgcontains(msg, prefixes[p] .. entry.keys[k]) then
						return entry
					end
				end
			end
		end
	end
	return nil
end

local function onMessage(cid, msg)
	local bp = matchBackpack(msg)
	if bp then
		-- YUR CHANGE: pre-check backpack space for bp (takes 1 slot for bp + 20 for runes)
		if getPlayerFreeSlots(cid) < 1 then
			selfSay('You do not have enough space in your backpack for that. Free up some slots first.')
			return
		end
		buyItemBackpack(cid, 1988, bp.itemid, bp.runeCharges or 1, BP_RUNES, backpackPrice(bp))
	elseif msgcontains(msg, 'price') or msgcontains(msg, 'prices') or msgcontains(msg, 'cost') or msgcontains(msg, 'how much') or msgcontains(msg, 'value') then
		local entry = npcFindCatalogEntry(msg, RUNE_BUYS) or npcFindCatalogEntry(msg, WAND_BUYS)
		if entry then
			local key = entry.keys[1]
			selfSay(string.upper(string.sub(key, 1, 1)) .. string.sub(key, 2) .. ': ' .. npcFormatPrice(entry.unitPrice) .. '.')
		else
			selfSay(RUNES_HELP)
		end
	elseif (msgcontains(msg, 'bp') or msgcontains(msg, 'backpack')) and (msgcontains(msg, 'mana') or msgcontains(msg, 'smp') or msgcontains(msg, 'life')) then
		selfSay('I do not sell fluid backpacks. The Seller in the temple does.')
	elseif npcTryCatalogBuyQuantity(cid, msg, RUNE_BUYS) then
		return
	elseif npcTryCatalogBuyQuantity(cid, msg, WAND_BUYS, 1) then
		return
	elseif npcIsHelp(msg) or msgcontains(msg, 'runes') then
		selfSay(RUNES_HELP)
	elseif msgcontains(msg, 'backpacks') or msgcontains(msg, 'rune backpacks') or msgcontains(msg, 'bps') then
		selfSay(RUNES_BACKPACKS)
	elseif msgcontains(msg, 'wands') or msgcontains(msg, 'rods') then
		selfSay(summarizeCatalog(WAND_BUYS, 'Magic weapons'))
	elseif msgcontains(msg, 'potions') or msgcontains(msg, 'potion') then
		selfSay('Mana fluid: 100gp. Strong mana potion: 250gp. Say "mana fluid", "3 mana fluid" or "smp".')
	else
		selfSay('I do not understand. Say "help" for prices.')
	end
end

npcDefine{
	greet = function(cid) return 'Hi ' .. creatureGetName(cid) .. '! I sell runes, rune backpacks, mana fluids, strong mana potions, wands and rods. Say "help" or "backpacks" for prices.' end,
	onMessage = onMessage,
}
