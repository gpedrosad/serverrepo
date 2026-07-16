focus = 0
talk_start = 0
target = 0
following = false
attacking = false

SELLER_HELP = 'I sell rope (50gp), shovel (20gp), backpack (10gp), mana fluid (100gp), life fluid (60gp), strong mana potion / SMP (250gp), backpack of mana fluid (2010gp), backpack of life fluid (1210gp), backpack of strong mana potion (5010gp), fishing rod (100gp) and torch (2gp). Weapons: serpent sword (2500gp), knight axe (2800gp), war hammer (3000gp). Knight gear: chain helmet 40gp, brass helmet 60gp, steel helmet 350gp, chain armor 120gp, brass armor 300gp, plate armor 800gp, knight armor 4500gp, brass legs 120gp, plate legs 900gp, knight legs 4500gp, brass shield 40gp, copper shield 60gp, plate shield 400gp, steel shield 1200gp, guardian shield 2500gp, leather boots 8gp. Say any amount, e.g. "3 rope". For full fluid backpacks, say "bp mana", "bp life", "bp smp", "bp strong mana" or "backpack strong mana potion". I buy empty vials (10gp each). You can also say sell all vials.'
SELLER_WEAPONS = 'Medium weapons: serpent sword 2500gp, knight axe 2800gp, war hammer 3000gp.'
SELLER_ARMORS = 'Knight gear: chain helmet 40gp, brass helmet 60gp, steel helmet 350gp, chain armor 120gp, brass armor 300gp, plate armor 800gp, knight armor 4500gp, brass legs 120gp, plate legs 900gp, knight legs 4500gp, brass shield 40gp, copper shield 60gp, plate shield 400gp, steel shield 1200gp, guardian shield 2500gp, leather boots 8gp.'
SELLER_SETS = 'Set progression for knights: basic = chain helmet, brass armor, brass legs, brass shield. Mid = steel helmet, plate armor, plate legs, plate shield. Advanced = knight armor, knight legs, steel shield or guardian shield.'
-- Match longer/more specific aliases first (strong mana before plain mana).
SELLER_FLUID_BACKPACKS = {
	{aliases = {'strong mana potion', 'strong mana', 'smp'}, fluidSubtype = 14, cost = 5010},
	{aliases = {'mana fluid', 'manafluid', 'mana'}, fluidSubtype = 7, cost = 2010},
	{aliases = {'life fluid', 'lifefluid', 'life'}, fluidSubtype = 10, cost = 1210},
}

SELLER_BUYS = {
	{keys = {'serpent sword', 'serpent'}, itemid = 2409, unitPrice = 2500},
	{keys = {'knight axe'}, itemid = 2430, unitPrice = 2800},
	{keys = {'war hammer', 'hammer'}, itemid = 2391, unitPrice = 3000},
	{keys = {'chain helmet'}, itemid = 2458, unitPrice = 40},
	{keys = {'brass helmet'}, itemid = 2460, unitPrice = 60},
	{keys = {'steel helmet'}, itemid = 2457, unitPrice = 350},
	{keys = {'chain armor'}, itemid = 2464, unitPrice = 120},
	{keys = {'brass armor'}, itemid = 2465, unitPrice = 300},
	{keys = {'plate armor'}, itemid = 2463, unitPrice = 800},
	{keys = {'knight armor'}, itemid = 2476, unitPrice = 4500},
	{keys = {'brass legs'}, itemid = 2478, unitPrice = 120},
	{keys = {'plate legs'}, itemid = 2647, unitPrice = 900},
	{keys = {'knight legs'}, itemid = 2477, unitPrice = 4500},
	{keys = {'brass shield'}, itemid = 2511, unitPrice = 40},
	{keys = {'copper shield'}, itemid = 2530, unitPrice = 60},
	{keys = {'plate shield'}, itemid = 2510, unitPrice = 400},
	{keys = {'steel shield'}, itemid = 2509, unitPrice = 1200},
	{keys = {'guardian shield', 'guardians shield'}, itemid = 2515, unitPrice = 2500},
	{keys = {'leather boots'}, itemid = 2643, unitPrice = 8},
	{keys = {'fishing rod', 'cana'}, itemid = 2580, unitPrice = 100},
	{keys = {'strong mana potion', 'strong mana', 'smp'}, itemid = 2006, fluidSubtype = 14, unitPrice = 250},
	{keys = {'manafluid', 'mana fluid'}, itemid = 2006, fluidSubtype = 7, unitPrice = 100},
	{keys = {'lifefluid', 'life fluid'}, itemid = 2006, fluidSubtype = 10, unitPrice = 60},
	{keys = {'backpack', 'mochila'}, itemid = 1988, unitPrice = 10},
	{keys = {'shovel', 'pala'}, itemid = 2554, unitPrice = 20},
	{keys = {'rope', 'cuerda'}, itemid = 2120, unitPrice = 50},
	{keys = {'torch', 'antorcha'}, itemid = 2050, unitPrice = 2},
}

function onThingMove(creature, thing, oldpos, oldstackpos)
end

function onCreatureAppear(creature)
end

function onCreatureDisappear(cid, pos)
	npcOnCreatureDisappear(cid)
end

function onCreatureTurn(creature)
end

local function sellerMatchFluidBackpack(msg)
	-- Match fluid backpacks before the generic catalog so
	-- "backpack mana fluid" does not buy a plain backpack.
	local prefixes = {'bp ', 'bp of ', 'bp de ', 'backpack ', 'backpack of ', 'backpack de ', 'mochila ', 'mochila de '}
	for i = 1, #SELLER_FLUID_BACKPACKS do
		local entry = SELLER_FLUID_BACKPACKS[i]
		for p = 1, #prefixes do
			for a = 1, #entry.aliases do
				if msgcontains(msg, prefixes[p] .. entry.aliases[a]) then
					return entry
				end
			end
		end
	end
	return nil
end

function sellerTryBuy(cid, msg)
	local fluidBackpack = sellerMatchFluidBackpack(msg)
	if fluidBackpack ~= nil then
		if getPlayerFreeSlots(cid) < 1 then
			selfSay('You do not have enough space in your backpack for that. Free up some slots first.')
			return true
		end
		buyFluidBackpack(cid, 1988, 2006, fluidBackpack.fluidSubtype, 20, fluidBackpack.cost)
		return true
	end

	local entry = npcFindCatalogBuyEntry(msg, SELLER_BUYS)
	if entry == nil then
		return false
	end

	local qty = npcParseBuyQuantity(msg)
	if entry.fluidSubtype ~= nil then
		buyFluidQty(cid, entry.itemid, entry.fluidSubtype, qty, entry.unitPrice * qty)
	else
		buy(cid, entry.itemid, qty, entry.unitPrice * qty)
	end
	return true
end

function onCreatureSay(cid, type, msg)
	msg = string.lower(msg)

	local state = npcHandleMessage(
		cid,
		msg,
		'Hi ' .. creatureGetName(cid) .. '! I sell supplies, fluid backpacks, weapons and knight gear. Say "help", "weapons", "armor" or "sets" for prices.'
	)
	if state ~= 'focused' then
		return
	end

	if npcIsHelp(msg) then
		selfSay(SELLER_HELP)
	elseif sellerTryBuy(cid, msg) then
		return
	elseif msgcontains(msg, 'weapons') or msgcontains(msg, 'weapon') or msgcontains(msg, 'armas') or msgcontains(msg, 'arma') then
		selfSay(SELLER_WEAPONS)
	elseif msgcontains(msg, 'armor') or msgcontains(msg, 'armors') or msgcontains(msg, 'armadura') or msgcontains(msg, 'armaduras') or msgcontains(msg, 'shield') or msgcontains(msg, 'shields') or msgcontains(msg, 'helmet') or msgcontains(msg, 'helmets') or msgcontains(msg, 'legs') or msgcontains(msg, 'boots') then
		selfSay(SELLER_ARMORS)
	elseif msgcontains(msg, 'set') or msgcontains(msg, 'sets') or msgcontains(msg, 'knight set') then
		selfSay(SELLER_SETS)
	elseif msgcontains(msg, 'sell all vials') or msgcontains(msg, 'sell all flasks') or msgcontains(msg, 'sell all frascos') then
		local emptyVials = getPlayerFluidCount(cid, 2006, 0)
		if emptyVials > 0 then
			sellFluid(cid, 2006, 0, emptyVials, emptyVials * 10)
		else
			selfSay('You do not have any empty vials to sell.')
		end
	elseif msgcontains(msg, 'vial') or msgcontains(msg, 'flask') or msgcontains(msg, 'frasco') then
		sellFluid(cid, 2006, 0, 1, 10)
	elseif msgcontains(msg, 'life') then
		local qty = npcParseBuyQuantity(msg)
		buyFluidQty(cid, 2006, 10, qty, 60 * qty)
	elseif msgcontains(msg, 'mana') then
		-- Fallback only for plain mana fluid. SMP is handled above via SELLER_BUYS /
		-- SELLER_FLUID_BACKPACKS ("strong mana", "smp", "bp smp", etc.).
		local qty = npcParseBuyQuantity(msg)
		buyFluidQty(cid, 2006, 7, qty, 100 * qty)
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
