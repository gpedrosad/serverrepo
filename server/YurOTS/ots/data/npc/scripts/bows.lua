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
		'Hello ' .. creatureGetName(cid) .. '! I sell crossbows (200gps), bows (100gps), arrows (100gps), bolts (150gps), power bolts (400gps) and spears (100gps).'
	)
	if state ~= 'focused' then
		return
	end

	if msgcontains(msg, 'distance') or msgcontains(msg, 'ammo') or msgcontains(msg, 'ammunition') then
		selfSay('Bolts: 50 for 150gps (say "bolts"). Power bolts: 50 for 400gps (say "power bolt"). Arrows: 50 for 100gps.')
	elseif msgcontains(msg, '100 power bolt') or msgcontains(msg, '100 power bolts') then
		buy(cid, 2547, 100, 800)
	elseif msgcontains(msg, 'power bolt') or msgcontains(msg, 'power bolts') then
		buy(cid, 2547, 50, 400)
	elseif msgcontains(msg, 'crossbow') then
		buy(cid, 2455, 1, 200)
	elseif msgcontains(msg, 'bow') then
		buy(cid, 2456, 1, 100)
	elseif msgcontains(msg, 'arrows') then
		buy(cid, 2544, 50, 100)
	elseif msgcontains(msg, 'bolts') and not string.find(msg, 'power') then
		buy(cid, 2543, 50, 150)
	elseif msgcontains(msg, 'spears') then
		buy(cid, 2389, 10, 100)
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
