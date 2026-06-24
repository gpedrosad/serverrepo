focus = 0
talk_start = 0
target = 0
following = false
attacking = false
talk_state = 0

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
		'Hello ' .. creatureGetName(cid) .. '! I sell premiums and promotions.'
	)
	if state ~= 'focused' then
		return
	end

	if msgcontains(msg, 'promotion') or msgcontains(msg, 'promote') then
		if isPromoted(cid) then
			selfSay('Sorry, you are already promoted.')
			talk_state = 0
		elseif getPlayerLevel(creatureGetName(cid)) < 20 then
			selfSay('Sorry, you need level 20 to buy promotion.')
			talk_state = 0
		elseif not isPremium(cid) then
			selfSay('Sorry, you must be premium to buy promotion.')
			talk_state = 0
		else
			selfSay('Do you want to buy promotion for 20k?')
			talk_state = 1
		end
	elseif msgcontains(msg, 'premium') or msgcontains(msg, 'premmy') then
		selfSay('Do you want to buy 10 premmy hours for 10k?')
		talk_state = 2
	elseif talk_state == 1 then
		if msgcontains(msg, 'yes') then
			if pay(cid, 20000) then
				selfSay('/promote ' .. creatureGetName(cid))
				selfSay('You are now promoted!')
			else
				selfSay('Sorry, you do not have enough money.')
			end
		end
		talk_state = 0
	elseif talk_state == 2 then
		if msgcontains(msg, 'yes') then
			if pay(cid, 10000) then
				selfSay('/premmy 10 ' .. creatureGetName(cid))
				selfSay('You have 10 premmy hours more!')
			else
				selfSay('Sorry, you do not have enough money.')
			end
		end
		talk_state = 0
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
