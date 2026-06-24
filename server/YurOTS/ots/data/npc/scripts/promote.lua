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
		'Hi ' .. creatureGetName(cid) .. '! I sell premium time and promotions. Say "premium" or "promotion".'
	)
	if state ~= 'focused' then
		return
	end

	if talk_state == 1 or talk_state == 2 then
		if talk_state == 1 then
			if npcHandlePendingYesNo(cid, msg, function()
				if pay(cid, 20000) then
					selfSay('/promote ' .. creatureGetName(cid))
					selfSay('Congratulations! You are now promoted!')
				else
					selfSay('Sorry, you need 20,000 gold.')
				end
			end) then
				talk_state = 0
			end
		elseif talk_state == 2 then
			if npcHandlePendingYesNo(cid, msg, function()
				if pay(cid, 10000) then
					selfSay('/premmy 10 ' .. creatureGetName(cid))
					selfSay('Done! You have 10 more premium hours.')
				else
					selfSay('Sorry, you need 10,000 gold.')
				end
			end) then
				talk_state = 0
			end
		end
		return
	end

	if msgcontains(msg, 'promotion') or msgcontains(msg, 'promote') then
		if isPromoted(cid) then
			selfSay('You are already promoted. Nice!')
		elseif getPlayerLevel(creatureGetName(cid)) < 20 then
			selfSay('You need level 20 to buy a promotion.')
		elseif not isPremium(cid) then
			selfSay('You need to be premium first. Say "premium" to buy time.')
		else
			selfSay('Promotion costs 20,000gp. Want to buy it? (yes or si)')
			talk_state = 1
		end
	elseif msgcontains(msg, 'premium') or msgcontains(msg, 'premmy') then
		selfSay('10 premium hours cost 10,000gp. Interested? (yes or si)')
		talk_state = 2
	elseif npcIsHelp(msg) then
		selfSay('Premium: 10 hours for 10k. Promotion: 20k (level 20+, premium required).')
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
