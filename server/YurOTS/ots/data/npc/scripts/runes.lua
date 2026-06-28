focus = 0
talk_start = 0
target = 0
following = false
attacking = false

RUNES_HELP = 'Runes: HMM 8gp, UH 40gp, GFB 20gp, explosion 20gp, SD 90gp, blank 5gp. Say any amount, e.g. "3 sd" or "10 uh". Rune backpacks: bp HMM 810gp, bp UH 810gp, bp GFB 1210gp, bp explosion 1210gp, bp SD 1810gp (20 runes each). Say "backpacks" for details. Mana fluid 100gp, strong mana potion (SMP) 250gp. Say "wands" or "rods" for magic weapons.'
RUNES_BACKPACKS = 'Rune backpacks: bp HMM 810gp, bp UH 810gp, bp GFB 1210gp, bp explosion 1210gp, bp SD 1810gp. Each backpack includes 20 runes plus the backpack.'

RUNE_BUYS = {
	{keys = {'sudden death', 'sd'}, itemid = 2268, unitPrice = 90, runeCharges = 1},
	{keys = {'ultimate healing', 'uh'}, itemid = 2273, unitPrice = 40, runeCharges = 1},
	{keys = {'great fireball', 'gfb'}, itemid = 2304, unitPrice = 20, runeCharges = 3},
	{keys = {'explosion'}, itemid = 2313, unitPrice = 20, runeCharges = 3},
	{keys = {'heavy magic missile', 'hmm'}, itemid = 2311, unitPrice = 8, runeCharges = 5},
	{keys = {'blank rune', 'blank'}, itemid = 2260, unitPrice = 5, itemQuantity = true},
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

	if npcIsHelp(msg) or msgcontains(msg, 'runes') then
		selfSay(RUNES_HELP)
	elseif msgcontains(msg, 'backpacks') or msgcontains(msg, 'rune backpacks') or msgcontains(msg, 'bps') then
		selfSay(RUNES_BACKPACKS)
	elseif msgcontains(msg, 'potions') or msgcontains(msg, 'potion') then
		selfSay('Mana fluid: 100gp. Strong mana potion: 250gp. Say "mana fluid", "3 mana fluid" or "smp".')
	elseif msgcontains(msg, 'wands') then
		selfSay('Wands: inferno 15k, plague 5k, cosmic energy 10k, vortex 500gp, dragonbreath 1k.')
	elseif msgcontains(msg, 'rods') then
		selfSay('Rods: quagmire 10k, snakebite 500gp, tempest 15k, volcanic 5k, moonlight 1k.')
	elseif msgcontains(msg, 'bp hmm') or msgcontains(msg, 'backpack hmm') or msgcontains(msg, 'backpack of hmm') then
		buyItemBackpack(cid, 1988, 2311, 5, 20, 810)
	elseif msgcontains(msg, 'bp uh') or msgcontains(msg, 'backpack uh') or msgcontains(msg, 'backpack of uh') or msgcontains(msg, 'bp ultimate healing') or msgcontains(msg, 'backpack of ultimate healing') then
		buyItemBackpack(cid, 1988, 2273, 1, 20, 810)
	elseif msgcontains(msg, 'bp gfb') or msgcontains(msg, 'backpack gfb') or msgcontains(msg, 'backpack of gfb') then
		buyItemBackpack(cid, 1988, 2304, 3, 20, 1210)
	elseif msgcontains(msg, 'bp explosion') or msgcontains(msg, 'backpack explosion') or msgcontains(msg, 'backpack of explosion') then
		buyItemBackpack(cid, 1988, 2313, 3, 20, 1210)
	elseif msgcontains(msg, 'bp sd') or msgcontains(msg, 'backpack sd') or msgcontains(msg, 'backpack of sd') or msgcontains(msg, 'bp sudden death') or msgcontains(msg, 'backpack of sudden death') then
		buyItemBackpack(cid, 1988, 2268, 1, 20, 1810)
	elseif npcTryCatalogBuyQuantity(cid, msg, RUNE_BUYS) then
		return
	elseif npcTryCatalogBuyQuantity(cid, msg, WAND_BUYS, 1) then
		return
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
