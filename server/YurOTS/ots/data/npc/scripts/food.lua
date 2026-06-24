focus = 0
talk_start = 0
target = 0
following = false
attacking = false

FOOD_HELP = 'Everything is 8gp: ham, meat, carrot, apple, brown bread, brown mushroom and egg. Just say what you want!'

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
	elseif msgcontains(msg, 'brown bread') or msgcontains(msg, 'bread') then
		buy(cid, 2691, 1, 8)
	elseif msgcontains(msg, 'ham') then
		buy(cid, 2671, 1, 8)
	elseif msgcontains(msg, 'carrot') then
		buy(cid, 2684, 1, 8)
	elseif msgcontains(msg, 'meat') then
		buy(cid, 2666, 1, 8)
	elseif msgcontains(msg, 'apple') then
		buy(cid, 2674, 1, 8)
	elseif msgcontains(msg, 'brown mushroom') or msgcontains(msg, 'mushroom') then
		buy(cid, 2789, 1, 8)
	elseif msgcontains(msg, 'egg') then
		buy(cid, 2695, 1, 8)
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
