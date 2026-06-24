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
		'Hi ' .. creatureGetName(cid) .. '! I sell scarf (1k gp) and amulet of loss / AOL (10k gp). Say "scarf" or "aol".'
	)
	if state ~= 'focused' then
		return
	end

	if npcIsHelp(msg) then
		selfSay('Scarf: 1000 gp. Amulet of loss (AOL): 10000 gp.')
	elseif msgcontains(msg, 'aol') or msgcontains(msg, 'amulet of loss') then
		buy(cid, 2173, 1, 10000)
	elseif msgcontains(msg, 'scarf') then
		buy(cid, 2661, 1, 1000)
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
