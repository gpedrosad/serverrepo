-- Ciclo de conversación: foco (un jugador a la vez), saludo/ocupado/despedida, timeout y alejarse, confirmaciones sí/no.
-- Parte de lib/npc.lua (ver docs/gameplay/NPC_SYSTEM.md).

function npcResetState()
	focus = 0
	talk_start = 0
	if talk_state ~= nil then
		talk_state = 0
	end
	if pending_exchange ~= nil then
		pending_exchange = nil
	end
	if pending_travel ~= nil then
		pending_travel = nil
	end
end

function npcBeginConversation(cid, message)
	if message ~= nil and message ~= '' then
		selfSay(message)
	end
	npcResetState()
	focus = cid
	talk_start = npcNow()
end

function npcTouchConversation(cid)
	if focus == cid then
		talk_start = npcNow()
		return true
	end
	return false
end

function npcEndConversation(cid, message)
	if cid ~= nil and cid ~= 0 then
		cancelPendingTrade(cid)
	end
	if message ~= nil and message ~= '' then
		selfSay(message)
	end
	npcResetState()
end

function npcHandleMessage(cid, msg, greetMessage, busyMessage, byeMessage)
	if npcIsGreeting(msg) and focus == 0 and getDistanceToCreature(cid) < 4 then
		npcBeginConversation(cid, greetMessage)
		return 'greet'
	end

	if npcIsGreeting(msg) and focus ~= cid and getDistanceToCreature(cid) < 4 then
		if busyMessage == nil or busyMessage == '' then
			busyMessage = 'One moment, ' .. creatureGetName(cid) .. '! I am helping someone else.'
		end
		selfSay(busyMessage)
		return 'busy'
	end

	if focus == cid and npcIsFarewell(msg) and getDistanceToCreature(cid) < 4 then
		if byeMessage == nil or byeMessage == '' then
			byeMessage = 'Bye, ' .. creatureGetName(cid) .. '! Come back anytime.'
		end
		npcEndConversation(cid, byeMessage)
		return 'bye'
	end

	if npcTouchConversation(cid) then
		return 'focused'
	end

	return nil
end

function npcOnCreatureDisappear(cid, message)
	if focus == cid then
		if message == nil or message == '' then
			message = 'See you later!'
		end
		npcEndConversation(cid, message)
	end
end

function npcOnThink(idleTimeout, idleMessage, maxDistance)
	if idleTimeout == nil then
		idleTimeout = 30
	end
	if maxDistance == nil then
		maxDistance = 5
	end

	if focus ~= 0 and (npcNow() - talk_start) > idleTimeout then
		if idleMessage == nil or idleMessage == '' then
			idleMessage = 'Next please...'
		end
		npcEndConversation(focus, idleMessage)
	elseif focus ~= 0 then
		local distance = getDistanceToCreature(focus)
		if distance == nil or distance > maxDistance then
			npcEndConversation(focus, 'See you later!')
		end
	end
end

function npcHandlePendingYesNo(cid, msg, onYes, onNo)
	if npcIsYes(msg) then
		if onYes then
			onYes()
		end
		return true
	end

	if npcIsNo(msg) then
		if onNo then
			onNo()
		else
			selfSay('No problem! Come back when you are ready.')
		end
		return true
	end

	return false
end
