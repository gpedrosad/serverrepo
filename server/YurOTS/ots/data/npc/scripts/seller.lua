focus = 0
talk_start = 0
target = 0
following = false
attacking = false

SELLER_HELP = 'I sell rope (50gp), shovel (20gp), backpack (10gp), mana fluid (100gp), life fluid (60gp), backpack of mana fluid (2010gp), backpack of life fluid (1210gp), fishing rod (100gp) and torch (2gp). Weapons: serpent sword (2500gp), knight axe (2800gp), war hammer (3000gp). Say any amount, e.g. "3 rope". I buy empty vials (10gp each). You can also say sell all vials.'
SELLER_WEAPONS = 'Medium weapons: serpent sword 2500gp, knight axe 2800gp, war hammer 3000gp.'

SELLER_BUYS = {
	{keys = {'bp mana fluid', 'bp of mana fluid', 'backpack of mana fluid', 'bp manafluid'}, special = 'bp_mana'},
	{keys = {'bp life fluid', 'bp of life fluid', 'backpack of life fluid', 'bp lifefluid'}, special = 'bp_life'},
	{keys = {'serpent sword', 'serpent'}, itemid = 2409, unitPrice = 2500},
	{keys = {'knight axe'}, itemid = 2430, unitPrice = 2800},
	{keys = {'war hammer', 'hammer'}, itemid = 2391, unitPrice = 3000},
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
		'Hi ' .. creatureGetName(cid) .. '! I sell supplies, fluid backpacks, serpent sword, knight axe and war hammer. Say "help" or "weapons" for prices.'
	)
	if state ~= 'focused' then
		return
	end

	if npcIsHelp(msg) then
		selfSay(SELLER_HELP)
	elseif msgcontains(msg, 'weapons') or msgcontains(msg, 'weapon') or msgcontains(msg, 'armas') or msgcontains(msg, 'arma') then
		selfSay(SELLER_WEAPONS)
	elseif sellerTryBuy(cid, msg) then
		return
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
