focus = 0
talk_start = 0
target = 0
following = false
attacking = false

ROOKEQ_HELP = 'Starter gear: katana/mace/hatchet 20gp, studded armor 30gp, chain armor 90gp, brass armor 300gp, brass helmet 20gp, leather helmet 5gp, brass shield 15gp, copper shield 50gp, leather legs 8gp, studded legs 20gp, leather boots 5gp, torch 2gp.'

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
	elseif msgcontains(msg, 'hatchet') then
		buy(cid, 2388, 1, 20)
	elseif msgcontains(msg, 'katana') then
		buy(cid, 2412, 1, 20)
	elseif msgcontains(msg, 'mace') then
		buy(cid, 2398, 1, 20)
	elseif msgcontains(msg, 'studded armor') then
		buy(cid, 2484, 1, 30)
	elseif msgcontains(msg, 'chain armor') then
		buy(cid, 2464, 1, 90)
	elseif msgcontains(msg, 'brass armor') then
		buy(cid, 2465, 1, 300)
	elseif msgcontains(msg, 'leather boots') then
		buy(cid, 2643, 1, 5)
	elseif msgcontains(msg, 'brass helmet') then
		buy(cid, 2460, 1, 20)
	elseif msgcontains(msg, 'leather helmet') then
		buy(cid, 2461, 1, 5)
	elseif msgcontains(msg, 'brass shield') then
		buy(cid, 2511, 1, 15)
	elseif msgcontains(msg, 'copper shield') then
		buy(cid, 2530, 1, 50)
	elseif msgcontains(msg, 'torch') then
		buy(cid, 2050, 1, 2)
	elseif msgcontains(msg, 'leather legs') then
		buy(cid, 2649, 1, 8)
	elseif msgcontains(msg, 'studded legs') then
		buy(cid, 2468, 1, 20)
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
