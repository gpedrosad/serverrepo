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
		'Hi ' .. creatureGetName(cid) .. '! I handle promotions. Say "promotion" if you are interested.'
	)
	if state ~= 'focused' then
		return
	end

	if talk_state == 1 then
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
		end
		return
	end

	if msgcontains(msg, 'promotion') or msgcontains(msg, 'promote') then
		if isPromoted(cid) then
			selfSay('You are already promoted. Nice!')
		elseif getPlayerLevel(creatureGetName(cid)) < 20 then
			selfSay('You need level 20 to buy a promotion.')
		elseif not isPremium(cid) then
			selfSay('You need to be premium first.')
		else
			selfSay('Promotion costs 20,000gp. Want to buy it? (yes or si)')
			talk_state = 1
		end
	elseif msgcontains(msg, 'premium') or msgcontains(msg, 'premmy') then
		selfSay('I do not sell premium time anymore.')
	elseif npcIsHelp(msg) then
		selfSay('Promotion costs 20,000gp and requires level 20 plus premium status.')
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
