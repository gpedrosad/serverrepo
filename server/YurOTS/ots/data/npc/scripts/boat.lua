focus = 0
talk_start = 0
target = 0
following = false
attacking = false
talk_state = 0
pending_travel = nil

TRAVELS = {
	{keys = {'dragon land'}, price = 50, dest = '122 119 7', name = 'Dragon Land'},
	{keys = {'city', 'the city'}, price = 20, dest = '171 65 7', name = 'The City'}
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

function matchTravel(msg)
	for i = 1, table.getn(TRAVELS) do
		local travel = TRAVELS[i]
		for j = 1, table.getn(travel.keys) do
			if msgcontains(msg, travel.keys[j]) then
				return travel
			end
		end
	end
	return nil
end

function doTravel(cid, travel)
	if pay(cid, travel.price) then
		selfSay('All aboard! Enjoy the trip!')
		selfSay('/send ' .. creatureGetName(cid) .. ', ' .. travel.dest)
		npcEndConversation(cid)
	else
		selfSay('Sorry, you need ' .. travel.price .. ' gold for that trip.')
	end
end

function offerTravel(cid, travel)
	pending_travel = travel
	talk_state = 1
	selfSay('A trip to ' .. travel.name .. ' costs ' .. travel.price .. 'gp. Ready to go? (yes or si)')
end

function onCreatureSay(cid, type, msg)
	msg = string.lower(msg)

	if npcIsGreeting(msg) and focus == 0 and getDistanceToCreature(cid) < 4 then
		if isPremium(cid) then
			npcBeginConversation(cid, 'Hi ' .. creatureGetName(cid) .. '! I sail to The City (20gp) or Dragon Land (50gp). Where do you want to go?')
		else
			selfSay('Sorry, only premium players can travel by boat.')
		end
		return
	end

	local state = npcHandleMessage(
		cid,
		msg,
		nil,
		'One moment, ' .. creatureGetName(cid) .. '!'
	)
	if state == 'busy' or state == 'bye' then
		return
	end

	if focus ~= cid then
		return
	end

	if talk_state == 1 then
		if npcHandlePendingYesNo(cid, msg, function()
			doTravel(cid, pending_travel)
		end) then
			talk_state = 0
			pending_travel = nil
		end
		return
	end

	if npcIsHelp(msg) then
		selfSay('The City: 20gp. Dragon Land: 50gp. Just say where you want to go!')
		return
	end

	local travel = matchTravel(msg)
	if travel then
		offerTravel(cid, travel)
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
