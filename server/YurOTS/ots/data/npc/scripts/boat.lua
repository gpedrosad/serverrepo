focus = 0
talk_start = 0
target = 0
following = false
attacking = false
talk_state = 0
pending_travel = nil

-- Script compartido por Nimral y Fargum.
-- dest = sqm exacto de aterrizaje. Viajar no cambia el temple del player.
ALL_TRAVELS = {
	{keys = {'elfland', 'elf land'}, price = 20, dest = '111 60 6', name = 'Elfland'},
	{keys = {'epstein island', 'epstein'}, price = 20, dest = '85 209 7', name = 'Epstein Island'},
	{keys = {'hell quest', 'hell'}, price = 20, dest = '347 168 7', name = 'Hell Quest'},
	{keys = {'dragon land'}, price = 50, dest = '122 119 7', name = 'Dragon Land'},
	{keys = {'alice maze', 'maze', 'laberinto'}, price = 20, dest = '413 103 7', name = 'Alice Maze'},
	{keys = {'gauntlet'}, price = 20, dest = '452 41 7', name = 'Gauntlet'},
	{keys = {'city', 'the city'}, price = 20, dest = '171 65 7', name = 'The City'}
}

function getTravels()
	return ALL_TRAVELS
end

function parsePosition(pos)
	local x, y, z = string.match(pos, '(%d+) (%d+) (%d+)')
	if not x or not y or not z then
		return nil
	end
	return tonumber(x), tonumber(y), tonumber(z)
end

function creatureIsAtPosition(cid, pos)
	local x, y, z = parsePosition(pos)
	if not x then
		return false
	end
	local px, py, pz = creatureGetPosition(cid)
	return px == x and py == y and pz == z
end

function travelSummary(travels)
	local parts = {}
	for i = 1, table.getn(travels) do
		local travel = travels[i]
		table.insert(parts, travel.name .. ' (' .. travel.price .. 'gp)')
	end
	return table.concat(parts, ', ')
end

function travelHelp(travels)
	local parts = {}
	for i = 1, table.getn(travels) do
		local travel = travels[i]
		local line = travel.name .. ': ' .. travel.price .. 'gp'
		table.insert(parts, line)
	end
	return table.concat(parts, '. ') .. '. Just say where you want to go!'
end

function canTravel(cid, travel)
	if creatureIsAtPosition(cid, travel.dest) then
		selfSay('You are already in ' .. travel.name .. '.')
		return false
	end
	return true
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

function matchTravel(msg, travels)
	for i = 1, table.getn(travels) do
		local travel = travels[i]
		for j = 1, table.getn(travel.keys) do
			if msgcontains(msg, travel.keys[j]) then
				return travel
			end
		end
	end
	return nil
end

function doTravel(cid, travel)
	if not canTravel(cid, travel) then
		return
	end
	if pay(cid, travel.price) then
		cancelPendingTrade(cid)
		npcResetState()
		selfSay('All aboard! Enjoy the trip!')
		local x, y, z = parsePosition(travel.dest)
		if x and y and z then
			travelPlayerTo(cid, x, y, z)
		end
	else
		selfSay('Sorry, you need ' .. travel.price .. ' gold for that trip.')
	end
end

function offerTravel(cid, travel)
	if not canTravel(cid, travel) then
		return
	end
	pending_travel = travel
	talk_state = 1
	selfSay('A trip to ' .. travel.name .. ' costs ' .. travel.price .. 'gp. Ready to go? (yes or si)')
end

function onCreatureSay(cid, type, msg)
	msg = string.lower(msg)
	local travels = getTravels()

	if npcIsGreeting(msg) and focus == 0 and getDistanceToCreature(cid) < 4 then
		npcBeginConversation(cid, 'Hi ' .. creatureGetName(cid) .. '! I sail to ' .. travelSummary(travels) .. '. Where do you want to go?')
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
		else
			selfSay('Please say yes or no.')
		end
		return
	end

	if npcIsHelp(msg) then
		selfSay(travelHelp(travels))
		return
	end

	local travel = matchTravel(msg, travels)
	if travel then
		offerTravel(cid, travel)
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
