focus = 0
talk_start = 0
target = 0
following = false
attacking = false

ROOKEQ_HELP = 'Starter gear: katana/mace/hatchet 20gp, studded armor 30gp, chain armor 90gp, brass armor 300gp, brass helmet 20gp, leather helmet 5gp, brass shield 15gp, copper shield 50gp, leather legs 8gp, studded legs 20gp, leather boots 5gp, torch 2gp. Say any amount, e.g. "3 torch".'

ROOKEQ_BUYS = {
	{keys = {'studded armor'}, itemid = 2484, unitPrice = 30},
	{keys = {'chain armor'}, itemid = 2464, unitPrice = 90},
	{keys = {'brass armor'}, itemid = 2465, unitPrice = 300},
	{keys = {'leather boots'}, itemid = 2643, unitPrice = 5},
	{keys = {'brass helmet'}, itemid = 2460, unitPrice = 20},
	{keys = {'leather helmet'}, itemid = 2461, unitPrice = 5},
	{keys = {'brass shield'}, itemid = 2511, unitPrice = 15},
	{keys = {'copper shield'}, itemid = 2530, unitPrice = 50},
	{keys = {'leather legs'}, itemid = 2649, unitPrice = 8},
	{keys = {'studded legs'}, itemid = 2468, unitPrice = 20},
	{keys = {'hatchet'}, itemid = 2388, unitPrice = 20},
	{keys = {'katana'}, itemid = 2412, unitPrice = 20},
	{keys = {'mace'}, itemid = 2398, unitPrice = 20},
	{keys = {'torch'}, itemid = 2050, unitPrice = 2},
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
		'Hi ' .. creatureGetName(cid) .. '! I sell starter weapons and armor for new adventurers. Say "help" for the full list.'
	)
	if state ~= 'focused' then
		return
	end

	if npcIsHelp(msg) then
		selfSay(ROOKEQ_HELP)
	elseif npcTryCatalogBuyQuantity(cid, msg, ROOKEQ_BUYS) then
		return
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
