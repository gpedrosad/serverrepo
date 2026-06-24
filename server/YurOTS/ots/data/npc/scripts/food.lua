focus = 0
talk_start = 0
target = 0
following = false
attacking = false

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
		'Hello ' .. creatureGetName(cid) .. '! I sell ham, meat, carrots, apples, brown breads, brown mushrooms and eggs (everything for 9gps).'
	)
	if state ~= 'focused' then
		return
	end

	if msgcontains(msg, 'brown bread') then
		buy(cid, 2691, 1, 8)
	elseif msgcontains(msg, 'ham') then
		buy(cid, 2671, 1, 8)
	elseif msgcontains(msg, 'carrot') then
		buy(cid, 2684, 1, 8)
	elseif msgcontains(msg, 'meat') then
		buy(cid, 2666, 1, 8)
	elseif msgcontains(msg, 'apple') then
		buy(cid, 2674, 1, 8)
	elseif msgcontains(msg, 'brown mushroom') then
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
