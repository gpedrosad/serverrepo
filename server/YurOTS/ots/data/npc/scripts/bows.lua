focus = 0
talk_start = 0
target = 0
following = false
attacking = false

BOWS_HELP = 'Crossbow 200gp, bow 100gp, arrows 2gp each, bolts 3gp each, power bolts 8gp each, spears 10gp each. Say any amount, e.g. "50 arrows" or "3 power bolts".'

BOW_BUYS = {
	{keys = {'power bolt', 'power bolts'}, itemid = 2547, unitPrice = 8},
	{keys = {'crossbow'}, itemid = 2455, unitPrice = 200},
	{keys = {'bow'}, itemid = 2456, unitPrice = 100},
	{keys = {'arrow', 'arrows'}, itemid = 2544, unitPrice = 2},
	{keys = {'bolt', 'bolts'}, itemid = 2543, unitPrice = 3},
	{keys = {'spear', 'spears'}, itemid = 2389, unitPrice = 10},
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
		'Hi ' .. creatureGetName(cid) .. '! ' .. BOWS_HELP
	)
	if state ~= 'focused' then
		return
	end

	if npcIsHelp(msg) or msgcontains(msg, 'distance') or msgcontains(msg, 'ammo') or msgcontains(msg, 'ammunition') then
		selfSay(BOWS_HELP)
	elseif npcTryCatalogBuyQuantity(cid, msg, BOW_BUYS) then
		return
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
