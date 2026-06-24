focus = 0
talk_start = 0
target = 0
following = false
attacking = false

BOWS_HELP = 'I sell crossbow (200gp), bow (100gp), arrows 50x (100gp), bolts 50x (150gp), power bolts 50x (400gp) and spears 10x (100gp). Just say the item name!'

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
	elseif msgcontains(msg, 'spears') or msgcontains(msg, 'spear') then
		buy(cid, 2389, 10, 100)
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
