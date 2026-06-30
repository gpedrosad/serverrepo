focus = 0
talk_start = 0
target = 0
following = false
attacking = false

RUNES_HELP = 'Runes: HMM 15gp, UH 200gp, GFB 45gp, explosion 35gp, SD 250gp, blank 10gp. Say any amount, e.g. "3 sd" or "10 uh". Rune backpacks: bp HMM 1500gp, bp UH 4000gp, bp GFB 2700gp, bp explosion 2100gp, bp SD 5000gp (20 runes each). Say "backpacks" for details. Mana fluid 100gp, strong mana potion (SMP) 250gp. Say "wands" or "rods" for magic weapons.'
RUNES_BACKPACKS = 'Rune backpacks: bp HMM 1500gp, bp UH 4000gp, bp GFB 2700gp, bp explosion 2100gp, bp SD 5000gp. Each backpack includes 20 runes plus the backpack.'

RUNE_BUYS = {
	{keys = {'sudden death', 'sd'}, itemid = 2268, unitPrice = 250, runeCharges = 1},
	{keys = {'ultimate healing', 'uh'}, itemid = 2273, unitPrice = 200, runeCharges = 1},
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

local function formatPrice(p)
	if p >= 1000 then
		local k = p / 1000
		if k == math.floor(k) then
			return tostring(k) .. 'k'
		end
		return string.format('%.1fk', k)
	end
	return tostring(p) .. 'gp'
end

local function summarizeCatalog(entries, groupName)
	local parts = {groupName .. ':'}
	for i = 1, table.getn(entries) do
		local entry = entries[i]
		parts[#parts + 1] = entry.keys[1] .. ' ' .. formatPrice(entry.unitPrice)
	end
	return table.concat(parts, ', ')
end

local function findCatalogBuy(msg, catalog)
	return npcFindCatalogBuyEntry(msg, catalog)
end

local function matchBackpack(msg)
	local prefixes = {'bp ', 'backpack ', 'backpack of '}
	for i = 1, table.getn(RUNE_BUYS) do
		local entry = RUNE_BUYS[i]
		if entry.runeCharges ~= nil then
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

function onThingMove(creature, thing, oldpos, oldstackpos)
end

function onCreatureAppear(creature)
end

function onCreatureDisappear(cid, pos)
	npcOnCreatureDisappear(cid)
end

function onCreatureTurn(creature)
end

function onCreatureSay(cid, type, msg)
	msg = string.lower(msg)

	local state = npcHandleMessage(
		cid,
		msg,
		'Hi ' .. creatureGetName(cid) .. '! I sell runes, rune backpacks, mana fluids, strong mana potions, wands and rods. Say "help" or "backpacks" for prices.'
	)
	if state ~= 'focused' then
		return
	end

	local bp = matchBackpack(msg)
	if bp then
		-- YUR CHANGE: pre-check backpack space for bp (takes 1 slot for bp + 20 for runes)
		if getPlayerFreeSlots(cid) < 1 then
			selfSay('You do not have enough space in your backpack for that. Free up some slots first.')
			return
		end
		buyItemBackpack(cid, 1988, bp.itemid, bp.runeCharges, 20, bp.unitPrice*20*bp.runeCharges)
	elseif msgcontains(msg, 'price') or msgcontains(msg, 'prices') or msgcontains(msg, 'cost') or msgcontains(msg, 'how much') or msgcontains(msg, 'value') then
		local entry = findCatalogBuy(msg, RUNE_BUYS) or findCatalogBuy(msg, WAND_BUYS)
		if entry then
			local key = entry.keys[1]
			selfSay(string.upper(string.sub(key, 1, 1)) .. string.sub(key, 2) .. ': ' .. formatPrice(entry.unitPrice) .. '.')
		else
			selfSay('Please specify an item. Say "help" for a list.')
		end
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

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
