-- Guild Master: fundar guild, unirse, invitar, expulsar, salir, pasar el liderazgo, vices y nicks.
-- Los datos viven en el C++ (guilds.cpp -> data/guilds.xml); este script es solo la charla.
-- Los nombres se toman del texto tal cual lo escribió el jugador (raw), no en minúsculas.
NONE, INVITED, MEMBER, VICE, LEADER = 0, 1, 2, 3, 4
LEADER_LEVEL = 50
MAX_NAME, MAX_RANK, MAX_NICK = 30, 20, 20
ALLOWED = '^[a-zA-Z0-9 %-]+$'

-- talk_state es 0 (sin pregunta pendiente) o la función que recibe la respuesta.
-- npcResetState lo vuelve a 0 al saludar o al cortar la charla.

local function trim(text)
	return (string.gsub(text, '^%s*(.-)%s*$', '%1'))
end

local function statusOf(name)
	return getPlayerGuildStatus(name)
end

local function guildOf(name)
	return getPlayerGuildName(name)
end

local function isOnline(name)
	return getPlayerLevel(name) >= 0
end

-- Nombre real si el jugador está online ("bob" -> "Bob"); si no, lo escrito.
local function playerName(text)
	local id = creatureGetName2(text)
	if id ~= 0 then
		return creatureGetName(id)
	end
	return text
end

local function sameName(a, b)
	return string.lower(a) == string.lower(b)
end

local function validText(text, maxLen, what)
	if string.len(text) > maxLen then
		selfSay('Sorry, ' .. what .. ' cannot be longer than ' .. maxLen .. ' characters.')
		return false
	end
	if not string.find(text, ALLOWED) then
		selfSay('Sorry, ' .. what .. ' contains illegal characters.')
		return false
	end
	return true
end

local function ask(question, nextStep)
	selfSay(question)
	talk_state = nextStep
end

-- Pregunta sí/no: cualquier otra respuesta deja la pregunta abierta.
local function askYesNo(question, onYes, noText)
	local function answer(msg)
		if npcIsYes(msg) then
			onYes()
		elseif npcIsNo(msg) then
			selfSay(noText)
		else
			talk_state = answer
		end
	end
	ask(question, answer)
end

-- Otro jugador de la misma guild que quien habla (nil y avisa si no).
local function guildMate(me, text)
	local name = playerName(text)
	if guildOf(name) == '' or guildOf(name) ~= guildOf(me) then
		selfSay('Sorry, ' .. name .. ' is not in your guild.')
		return nil
	end
	return name
end

-- found ---------------------------------------------------------------------------------------
local function foundGuild(me)
	local newName
	local function getRank(_, raw)
		local rank = trim(raw)
		if not validText(rank, MAX_RANK, 'rank name') then
			return
		end
		if statusOf(me) > INVITED then
			selfSay('Sorry, you are member of a guild.')
		elseif foundNewGuild(newName) == 0 then	-- se crea recién acá: un "found" abandonado no deja guilds vacías
			selfSay('Sorry, there is already a guild with that name.')
		else
			setPlayerGuild(me, LEADER, rank, newName)	-- si estaba invitado a otra, el C++ lo saca de esa
			selfSay('You are now leader of ' .. newName .. '.')
		end
	end
	local function getName(_, raw)
		newName = trim(raw)
		if validText(newName, MAX_NAME, 'guild name') then
			ask('And what rank do you wish to have?', getRank)
		end
	end

	if getPlayerLevel(me) < LEADER_LEVEL then
		selfSay('Sorry, you need level ' .. LEADER_LEVEL .. ' to found a guild.')
	elseif statusOf(me) > INVITED then
		selfSay('Sorry, you are member of a guild.')
	else
		ask('What name should your guild have?', getName)
	end
end

-- join / leave --------------------------------------------------------------------------------
local function joinGuild(me)
	local status = statusOf(me)
	if status == NONE then
		selfSay('Sorry, you are not invited to any guild.')
	elseif status > INVITED then
		selfSay('Sorry, you are a member of a guild.')
	else
		askYesNo('Do you want to join ' .. guildOf(me) .. '? (yes or si)', function()
			if statusOf(me) == INVITED then
				setPlayerGuildStatus(me, MEMBER)
				selfSay('Welcome! You are now a guild member.')
			end
		end, 'No problem! What else can I do for you?')
	end
end

local function leaveGuild(me)
	local status = statusOf(me)
	local question = 'Do you want to leave ' .. guildOf(me) .. '? (yes or si)'
	if status == NONE or status == INVITED then
		selfSay('You are not in a guild.')
		return
	elseif status == LEADER then
		question = 'You are the guild leader. If you leave, no one can invite new players. Are you sure? (yes or si)'
	end
	askYesNo(question, function()
		if statusOf(me) > INVITED then
			clearPlayerGuild(me)
			selfSay('You have left your guild. Take care!')
		end
	end, 'Glad you stayed! What else can I do for you?')
end

-- invite / kick -------------------------------------------------------------------------------
local function invitePlayer(me)
	if statusOf(me) < VICE then
		selfSay('Sorry, only leader and vice-leaders can invite players to a guild.')
		return
	end
	ask('Who do you want to invite to your guild?', function(_, raw)
		local name = playerName(trim(raw))
		if not isOnline(name) then
			selfSay('Sorry, ' .. name .. ' is not online.')
		elseif statusOf(name) > INVITED then
			selfSay('Sorry, ' .. name .. ' is already in a guild.')
		else
			ask('And what rank do you wish to give him/her?', function(_, rankRaw)
				local rank = trim(rankRaw)
				if validText(rank, MAX_RANK, 'rank name') and statusOf(me) >= VICE then
					setPlayerGuild(name, INVITED, rank, guildOf(me))
					selfSay('You have invited ' .. name .. ' to your guild.')
				end
			end)
		end
	end)
end

local function kickPlayer(me)
	if statusOf(me) < VICE then
		selfSay('Sorry, only leader and vice-leaders can kick players from a guild.')
		return
	end
	ask('Who do you want to kick today?', function(_, raw)
		local text = trim(raw)
		if sameName(text, me) then
			selfSay('To kick yourself say leave.')
			return
		end
		local name = guildMate(me, text)
		if name == nil then
			return
		end
		if statusOf(me) > statusOf(name) then
			clearPlayerGuild(name)
			selfSay('You kicked ' .. name .. ' from your guild.')
		else
			selfSay('Sorry, vice-leaders can kick only regular members.')
		end
	end)
end

-- leader only: pass, vice, member, nick -------------------------------------------------------
local function leaderOnly(me, deny)
	if statusOf(me) ~= LEADER then
		selfSay(deny)
		return false
	end
	return true
end

-- Pide el nombre de un compañero de guild (no uno mismo) y llama a action(name, status).
local function askMate(me, question, action)
	ask(question, function(_, raw)
		local text = trim(raw)
		if sameName(text, me) then
			selfSay('To resign from leadership say pass.')
			return
		end
		local name = guildMate(me, text)
		if name == nil then
			return
		end
		local status = statusOf(name)
		if status == INVITED then
			selfSay('Sorry, ' .. name .. ' hasn\'t joined your guild yet.')
		elseif statusOf(me) == LEADER then
			action(name, status)
		end
	end)
end

local function passLeadership(me)
	if not leaderOnly(me, 'Sorry, only the leader can pass the leadership.') then
		return
	end
	askMate(me, 'Who do you want to be the new leader?', function(name)
		if getPlayerLevel(name) < 0 then
			selfSay('Sorry, ' .. name .. ' is not online.')
		elseif getPlayerLevel(name) < LEADER_LEVEL then
			selfSay('Sorry, the new leader needs level ' .. LEADER_LEVEL .. '.')
		else
			setPlayerGuildStatus(me, MEMBER)
			setPlayerGuildStatus(name, LEADER)
			selfSay(name .. ' is the new leader of ' .. guildOf(name) .. '.')
		end
	end)
end

local function promoteVice(me)
	if not leaderOnly(me, 'Sorry, only the leader can promote members to vice-leader.') then
		return
	end
	askMate(me, 'Which member do you want to promote to vice-leader?', function(name, status)
		if status == VICE then
			selfSay(name .. ' is already a vice-leader.')
		else
			setPlayerGuildStatus(name, VICE)
			selfSay(name .. ' is now a vice-leader of your guild.')
		end
	end)
end

local function demoteVice(me)
	if not leaderOnly(me, 'Sorry, only the leader can demote vice-leaders to members.') then
		return
	end
	askMate(me, 'Which vice-leader do you want to demote to regular member?', function(name, status)
		if status == MEMBER then
			selfSay(name .. ' is already a regular member.')
		else
			setPlayerGuildStatus(name, MEMBER)
			selfSay(name .. ' is now a regular member of your guild.')
		end
	end)
end

local function changeNick(me)
	if not leaderOnly(me, 'Sorry, only the leader can change nicks.') then
		return
	end
	ask('Whose nick do you want to change?', function(_, raw)
		local name = guildMate(me, trim(raw))
		if name == nil then
			return
		end
		ask('And what nick do you want him/her to have (say none to clear)?', function(msg, nickRaw)
			local nick = trim(nickRaw)
			if msg == 'none' then
				setPlayerGuildNick(name, '')
				selfSay(name .. ' now has no nick.')
			elseif validText(nick, MAX_NICK, 'nick') then
				setPlayerGuildNick(name, nick)
				selfSay('You have changed ' .. name .. '\'s nick.')
			end
		end)
	end)
end

COMMANDS = {
	{keys = {'found'}, run = foundGuild},
	{keys = {'join'}, run = joinGuild},
	{keys = {'kick', 'exclude'}, run = kickPlayer},
	{keys = {'invite'}, run = invitePlayer},
	{keys = {'leave'}, run = leaveGuild},
	{keys = {'pass'}, run = passLeadership},
	{keys = {'vice'}, run = promoteVice},
	{keys = {'member'}, run = demoteVice},
	{keys = {'nick', 'title'}, run = changeNick},
}

local function onMessage(cid, msg, raw)
	local me = creatureGetName(cid)
	if talk_state ~= 0 then
		local step = talk_state
		talk_state = 0
		talk_start = npcNow()
		step(msg, raw or msg)
		return
	end
	if npcIsHelp(msg) then
		selfSay('Commands: found (create guild), join, invite, kick, leave, pass (new leader), vice, member, nick.')
		return
	end
	for i = 1, table.getn(COMMANDS) do
		if npcMatchesAny(msg, COMMANDS[i].keys) then
			talk_start = npcNow()
			COMMANDS[i].run(me)
			return
		end
	end
end

npcDefine{
	greet = function(cid) return 'Hi ' .. creatureGetName(cid) .. '! I handle guild business. Say "help" to see what you can do.' end,
	busy = function(cid) return 'One moment, ' .. creatureGetName(cid) .. '!' end,
	state = {talk_state = 0},
	idleTimeout = 45,
	onMessage = onMessage,
}
