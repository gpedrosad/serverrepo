-- The Oracle (Rookgaard): elegir vocación y viajar al continente.
talk_state = 0
cname = ''
vocation = 0
mainlevel = 8

local function onMessage(cid, msg)
	cname = creatureGetName(cid)
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
			-- Templo actual (mapa once). Portales templo viejo: 159 wave arena, 160 hunt plano, 162 pisos.
			setPlayerMasterPos(cid, 130, 53, 6)
			selfSay('/send ' .. cname .. ', 130 53 6')
			npcEndConversation(cid)
		else
			selfSay('Just say "city" when you want me to send you to the mainland.')
			talk_state = 3
		end
	end
end

npcDefine{
	greet = function(cid) return 'Hi ' .. creatureGetName(cid) .. '! Are you ready to leave Rookgaard and choose your vocation? (yes or si)' end,
	idleTimeout = 45,
	onMessage = onMessage,
}
