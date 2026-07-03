focus = 0
talk_start = 0
target = 0
following = false
attacking = false

SELLER_HELP = 'I sell rope (50gp), shovel (20gp), backpack (10gp), mana fluid (100gp), life fluid (60gp), backpack of mana fluid (2010gp), backpack of life fluid (1210gp), fishing rod (100gp) and torch (2gp). Weapons: serpent sword (2500gp), knight axe (2800gp), war hammer (3000gp). Knight gear: chain helmet 40gp, brass helmet 60gp, steel helmet 350gp, chain armor 120gp, brass armor 300gp, plate armor 800gp, knight armor 4500gp, brass legs 120gp, plate legs 900gp, knight legs 4500gp, brass shield 40gp, copper shield 60gp, plate shield 400gp, steel shield 1200gp, guardian shield 2500gp, leather boots 8gp. Say any amount, e.g. "3 rope". I buy empty vials (10gp each). You can also say sell all vials.'
SELLER_WEAPONS = 'Medium weapons: serpent sword 2500gp, knight axe 2800gp, war hammer 3000gp.'
SELLER_ARMORS = 'Knight gear: chain helmet 40gp, brass helmet 60gp, steel helmet 350gp, chain armor 120gp, brass armor 300gp, plate armor 800gp, knight armor 4500gp, brass legs 120gp, plate legs 900gp, knight legs 4500gp, brass shield 40gp, copper shield 60gp, plate shield 400gp, steel shield 1200gp, guardian shield 2500gp, leather boots 8gp.'
SELLER_SETS = 'Set progression for knights: basic = chain helmet, brass armor, brass legs, brass shield. Mid = steel helmet, plate armor, plate legs, plate shield. Advanced = knight armor, knight legs, steel shield or guardian shield.'

SELLER_BUYS = {
	{keys = {'bp mana fluid', 'bp of mana fluid', 'backpack of mana fluid', 'bp manafluid'}, special = 'bp_mana'},
	{keys = {'bp life fluid', 'bp of life fluid', 'backpack of life fluid', 'bp lifefluid'}, special = 'bp_life'},
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

function sellerTryBuy(cid, msg)
	local entry = npcFindCatalogBuyEntry(msg, SELLER_BUYS)
	if entry == nil then
		return false
	end

	if entry.special == 'bp_mana' then
		buyFluidBackpack(cid, 1988, 2006, 7, 20, 2010)
		return true
	end
	if entry.special == 'bp_life' then
		buyFluidBackpack(cid, 1988, 2006, 10, 20, 1210)
		return true
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
		local qty = npcParseBuyQuantity(msg)
		buyFluidQty(cid, 2006, 7, qty, 100 * qty)
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
