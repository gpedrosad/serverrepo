focus = 0
talk_start = 0
target = 0
following = false
attacking = false

FOOD_HELP = 'Everything is 8gp: ham, meat, carrot, apple, brown bread, brown mushroom and egg. Say any amount, e.g. "5 ham".'

FOOD_BUYS = {
	{keys = {'brown bread', 'bread'}, itemid = 2691, unitPrice = 8},
	{keys = {'brown mushroom', 'mushroom'}, itemid = 2789, unitPrice = 8},
	{keys = {'ham'}, itemid = 2671, unitPrice = 8},
	{keys = {'carrot'}, itemid = 2684, unitPrice = 8},
	{keys = {'meat'}, itemid = 2666, unitPrice = 8},
	{keys = {'apple'}, itemid = 2674, unitPrice = 8},
	{keys = {'egg'}, itemid = 2695, unitPrice = 8},
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
		'Hi ' .. creatureGetName(cid) .. '! ' .. FOOD_HELP
	)
	if state ~= 'focused' then
		return
	end

	if npcIsHelp(msg) then
		selfSay(FOOD_HELP)
	elseif npcTryCatalogBuyQuantity(cid, msg, FOOD_BUYS) then
		return
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
