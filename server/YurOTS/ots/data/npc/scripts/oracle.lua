-- The Oracle (Rookgaard): elegir vocación y viajar al continente. Solo para jugadores sin vocación.
talk_state = 0      -- 0 pregunta inicial, 1 elegir vocación, 2 confirmar, 3 decir "city"
vocation = 0
MIN_LEVEL = 8
TEMPLE = {130, 53, 6} -- templo del continente
VOCATIONS = {
	{key = 'sorcerer', id = 1, text = 'A mighty sorcerer!'},
	{key = 'druid', id = 2, text = 'A wise druid!'},
	{key = 'paladin', id = 3, text = 'A skilled paladin!'},
	{key = 'knight', id = 4, text = 'A brave knight!'},
}

local function hasVocation(cid)
	return getPlayerVocation(cid) ~= 0
end

local function onMessage(cid, msg)
	if hasVocation(cid) then -- antes cualquiera podía volver y cambiar de vocación gratis
		selfSay('You already have a vocation. My work with you is done.')
		npcEndConversation(cid)
		return
	end

	if talk_state == 0 then
		if npcIsYes(msg) then
			if getPlayerLevel(creatureGetName(cid)) >= MIN_LEVEL then
				selfSay('Wonderful! Choose your path: knight, paladin, sorcerer or druid?')
				talk_state = 1
			else
				selfSay('Come back at level ' .. MIN_LEVEL .. ' and we will talk again.')
			end
		elseif npcIsNo(msg) then
			selfSay('No rush! Come back when you feel ready.')
		end
	elseif talk_state == 1 then
		for i = 1, table.getn(VOCATIONS) do
			local v = VOCATIONS[i]
			if msgcontains(msg, v.key) then
				vocation = v.id
				talk_state = 2
				selfSay(v.text .. ' Are you sure? (yes or si)')
				return
			end
		end
		selfSay('I did not catch that. Say knight, paladin, sorcerer or druid.')
	elseif talk_state == 2 then
		if npcIsYes(msg) then
			selfSay('Great choice! Say "city" when you are ready to travel to the mainland.')
			talk_state = 3
		elseif npcIsNo(msg) then
			selfSay('No problem! Which vocation would you like instead?')
			talk_state = 1
		end
	elseif talk_state == 3 then
		if msgcontains(msg, 'city') then
			local name = creatureGetName(cid)
			selfSay('Good luck out there, ' .. name .. '!')
			setPlayerVocation(cid, vocation)
			setPlayerMasterPos(cid, TEMPLE[1], TEMPLE[2], TEMPLE[3])
			selfSay('/send ' .. name .. ', ' .. TEMPLE[1] .. ' ' .. TEMPLE[2] .. ' ' .. TEMPLE[3])
			npcEndConversation(cid)
		else
			selfSay('Just say "city" when you want me to send you to the mainland.')
		end
	end
end

npcDefine{
	greet = function(cid)
		if hasVocation(cid) then
			return 'Hello ' .. creatureGetName(cid) .. '. You already chose your path.'
		end
		return 'Hi ' .. creatureGetName(cid) .. '! Are you ready to leave Rookgaard and choose your vocation? (yes or si)'
	end,
	state = {talk_state = 0, vocation = 0},
	idleTimeout = 45,
	onMessage = onMessage,
}
