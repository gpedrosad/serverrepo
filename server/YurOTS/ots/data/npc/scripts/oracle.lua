focus = 0
talk_start = 0
target = 0
following = false
attacking = false
talk_state = 0
cname = ''
vocation = 0
mainlevel = 8

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
	cname = creatureGetName(cid)
	msg = string.lower(msg)

	local state = npcHandleMessage(
		cid,
		msg,
		'Hi ' .. cname .. '! Are you ready to leave Rookgaard and choose your vocation? (yes or si)'
	)
	if state ~= 'focused' then
		return
	end

	if talk_state == 0 then
		if npcIsYes(msg) then
			level = getPlayerLevel(cname)
			if level >= mainlevel then
				selfSay('Wonderful! Choose your path: knight, paladin, sorcerer or druid?')
				talk_state = 1
			else
				selfSay('Come back at level ' .. mainlevel .. ' and we will talk again.')
				talk_state = 0
			end
		elseif npcIsNo(msg) then
			selfSay('No rush! Come back when you feel ready.')
			talk_state = 0
		end
	elseif talk_state == 1 then
		talk_state = 2
		if msgcontains(msg, 'sorcerer') then
			selfSay('A mighty sorcerer! Are you sure? (yes or si)')
			vocation = 1
		elseif msgcontains(msg, 'druid') then
			selfSay('A wise druid! Are you sure? (yes or si)')
			vocation = 2
		elseif msgcontains(msg, 'paladin') then
			selfSay('A skilled paladin! Are you sure? (yes or si)')
			vocation = 3
		elseif msgcontains(msg, 'knight') then
			selfSay('A brave knight! Are you sure? (yes or si)')
			vocation = 4
		else
			selfSay('I did not catch that. Say knight, paladin, sorcerer or druid.')
			vocation = 0
			talk_state = 1
		end
	elseif talk_state == 2 then
		if npcIsYes(msg) then
			if vocation > 0 then
				selfSay('Great choice! Say "city" when you are ready to travel to the mainland.')
				talk_state = 3
			end
		elseif npcIsNo(msg) then
			selfSay('No problem! Which vocation would you like instead?')
			talk_state = 1
		end
	elseif talk_state == 3 then
		if msgcontains(msg, 'city') then
			selfSay('Good luck out there, ' .. cname .. '!')
			setPlayerVocation(cid, vocation)
			setPlayerMasterPos(cid, 160, 54, 7)
			selfSay('/send ' .. cname .. ', 160 54 7')
			npcEndConversation(cid)
		else
			selfSay('Just say "city" when you want me to send you to the mainland.')
			talk_state = 3
		end
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink(45)
end
