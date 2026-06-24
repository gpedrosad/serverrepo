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

	if msgcontains(msg, 'hi') and focus == 0 and getDistanceToCreature(cid) < 4 then
		if isPremium(cid) then
			npcBeginConversation(cid, 'Hello ' .. creatureGetName(cid) .. '! I can take you to the The City (20gp) or Dragon Land (50gp). Where do you want to go?')
		else
			selfSay('Sorry, only premium players can travel by boat.')
		end
		return
	end

	if msgcontains(msg, 'hi') and focus ~= cid and getDistanceToCreature(cid) < 4 then
		selfSay('Sorry, ' .. creatureGetName(cid) .. '! I talk to you in a minute.')
		return
	end

	if not npcTouchConversation(cid) then
		return
	end

	if msgcontains(msg, 'dragon land') then
		if pay(cid, 50) then
			selfSay('Let\'s go!')
			selfSay('/send ' .. creatureGetName(cid) .. ', 122 119 7')
			npcEndConversation(cid)
		else
			selfSay('Sorry, you don\'t have enough money.')
		end
	elseif msgcontains(msg, 'city') then
		if pay(cid, 20) then
			selfSay('Let\'s go!')
			selfSay('/send ' .. creatureGetName(cid) .. ', 171 65 7')
			npcEndConversation(cid)
		else
			selfSay('Sorry, you don\'t have enough money.')
		end
	elseif msgcontains(msg, 'bye') and getDistanceToCreature(cid) < 4 then
		npcEndConversation(cid, 'Good bye, ' .. creatureGetName(cid) .. '!')
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
