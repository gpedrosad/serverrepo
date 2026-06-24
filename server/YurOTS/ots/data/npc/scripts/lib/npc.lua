-- get the distance to a creature
function getDistanceToCreature(id)
	if id == 0 or id == nil then
		selfGotoIdle()
	end
	cx, cy, cz = creatureGetPosition(id)
	if cx == nil then
		return nil
	end
	sx, sy, sz = selfGetPosition()
	return math.max(math.abs(sx-cx), math.abs(sy-cy))
end

function msgcontains(txt, str)
	return (string.find(txt, str) and not string.find(txt, '(%w+)' .. str) and not string.find(txt, str .. '(%w+)'))
end

-- do one step to reach position
function moveToPosition(x, y, z)
	selfMoveTo(x, y, z)
end

-- do one step to reach creature
function moveToCreature(id)
	if id == 0 or id == nil then
		selfGotoIdle()
	end
	tx, ty, tz = creatureGetPosition(id)
	if tx == nil then
		selfGotoIdle()
	else
		moveToPosition(tx, ty, tz)
	end
end

function selfGotoIdle()
	following = false
	attacking = false
	selfAttackCreature(0)
	target = 0
end

function npcResetState()
	focus = 0
	talk_start = 0
	if talk_state ~= nil then
		talk_state = 0
	end
end

function npcBeginConversation(cid, message)
	if message ~= nil and message ~= '' then
		selfSay(message)
	end
	focus = cid
	talk_start = os.clock()
	if talk_state ~= nil then
		talk_state = 0
	end
end

function npcTouchConversation(cid)
	if focus == cid then
		talk_start = os.clock()
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
	if msgcontains(msg, 'hi') and focus == 0 and getDistanceToCreature(cid) < 4 then
		npcBeginConversation(cid, greetMessage)
		return 'greet'
	end

	if msgcontains(msg, 'hi') and focus ~= cid and getDistanceToCreature(cid) < 4 then
		if busyMessage == nil or busyMessage == '' then
			busyMessage = 'Sorry, ' .. creatureGetName(cid) .. '! I talk to you in a minute.'
		end
		selfSay(busyMessage)
		return 'busy'
	end

	if focus == cid and msgcontains(msg, 'bye') and getDistanceToCreature(cid) < 4 then
		if byeMessage == nil or byeMessage == '' then
			byeMessage = 'Good bye, ' .. creatureGetName(cid) .. '!'
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
			message = 'Good bye then.'
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

	if focus ~= 0 and (os.clock() - talk_start) > idleTimeout then
		if idleMessage == nil or idleMessage == '' then
			idleMessage = 'Next Please...'
		end
		npcEndConversation(focus, idleMessage)
	elseif focus ~= 0 then
		local distance = getDistanceToCreature(focus)
		if distance == nil or distance > maxDistance then
			npcEndConversation(focus, 'Good bye then.')
		end
	end
end

function npcMatchesAny(msg, keys)
	if type(keys) == 'string' then
		return msgcontains(msg, keys)
	end

	for i = 1, table.getn(keys) do
		if msgcontains(msg, keys[i]) then
			return true
		end
	end

	return false
end

function npcFindCatalogEntry(msg, entries)
	for i = 1, table.getn(entries) do
		local entry = entries[i]
		if npcMatchesAny(msg, entry.keys) then
			return entry
		end
	end

	return nil
end

function npcTryCatalogReply(msg, entries)
	local entry = npcFindCatalogEntry(msg, entries)
	if entry and entry.reply then
		selfSay(entry.reply)
		return true
	end

	return false
end

function npcTryCatalogBuy(cid, msg, entries)
	local entry = npcFindCatalogEntry(msg, entries)
	if entry then
		buy(cid, entry.itemid, entry.count or 1, entry.price)
		return true
	end

	return false
end

function npcTryCatalogSell(cid, msg, entries)
	local entry = npcFindCatalogEntry(msg, entries)
	if entry then
		sell(cid, entry.itemid, entry.count or 1, entry.price)
		return true
	end

	return false
end
