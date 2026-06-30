-- Shared NPC helpers. Dialogue in English; accepts English and Spanish player replies.

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

function moveToPosition(x, y, z)
	selfMoveTo(x, y, z)
end

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

function npcIsGreeting(msg)
	return msgcontains(msg, 'hi') or msgcontains(msg, 'hola') or msgcontains(msg, 'buenas') or msgcontains(msg, 'hey')
end

function npcIsFarewell(msg)
	return msgcontains(msg, 'bye') or msgcontains(msg, 'adios') or msgcontains(msg, 'chau') or msgcontains(msg, 'chao')
end

function npcIsYes(msg)
	if msg == 'y' or msg == 's' or msg == 'si' or msg == 'sí' then
		return true
	end
	return msgcontains(msg, 'yes') or msgcontains(msg, 'sip') or msgcontains(msg, 'dale')
end

function npcIsNo(msg)
	if msg == 'n' then
		return true
	end
	return msgcontains(msg, 'no') or msgcontains(msg, 'nop')
end

function npcIsHelp(msg)
	return msgcontains(msg, 'help') or msgcontains(msg, 'ayuda') or msgcontains(msg, 'list')
		or msgcontains(msg, 'lista') or msgcontains(msg, 'offer') or msgcontains(msg, 'oferta')
		or msgcontains(msg, 'prices') or msgcontains(msg, 'precios') or msgcontains(msg, 'trade')
		or msgcontains(msg, 'info')
end

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
	focus = cid
	talk_start = os.clock()
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

	if focus ~= 0 and (os.clock() - talk_start) > idleTimeout then
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
		local qty = entry.count or 1
		local price = entry.price or (entry.unitPrice * qty)
		buy(cid, entry.itemid, qty, price)
		return true
	end

	return false
end

function npcParseBuyQuantity(msg, maxQty)
	maxQty = maxQty or 100
	local qty = tonumber(string.match(msg, '(%d+)'))
	if qty == nil or qty < 1 then
		return 1
	end
	if qty > maxQty then
		return maxQty
	end
	return qty
end

function npcCatalogKeyLength(entry)
	local keys = entry.keys
	if type(keys) == 'string' then
		return string.len(keys)
	end

	local maxLen = 0
	for i = 1, table.getn(keys) do
		local len = string.len(keys[i])
		if len > maxLen then
			maxLen = len
		end
	end
	return maxLen
end

function npcFindMatchOffset(msg, keys)
	if type(keys) == 'string' then
		keys = {keys}
	end
	local bestOffset = nil
	local bestLen = 0
	for i = 1, table.getn(keys) do
		local key = keys[i]
		local start = 1
		while true do
			local s = string.find(msg, key, start, true)
			if not s then break end
			local leftOk = (s == 1) or string.match(string.sub(msg, s-1, s-1), '%W') ~= nil
			local e = s + string.len(key) - 1
			local rightOk = (e >= string.len(msg)) or string.match(string.sub(msg, e+1, e+1), '%W') ~= nil
			if leftOk and rightOk then
				if bestOffset == nil or s < bestOffset or (s == bestOffset and string.len(key) > bestLen) then
					bestOffset = s
					bestLen = string.len(key)
				end
			end
			start = s + 1
		end
	end
	return bestOffset, bestLen
end

function npcFindCatalogBuyEntry(msg, entries)
	local best = nil
	local bestOffset = math.huge
	local bestLen = 0

	for i = 1, table.getn(entries) do
		local entry = entries[i]
		local offset, len = npcFindMatchOffset(msg, entry.keys)
		if offset ~= nil then
			if offset < bestOffset or (offset == bestOffset and len > bestLen) then
				best = entry
				bestOffset = offset
				bestLen = len
			end
		end
	end

	return best
end

function npcTryCatalogBuyQuantity(cid, msg, entries, maxQty)
	local entry = npcFindCatalogBuyEntry(msg, entries)
	if entry == nil then
		return false
	end

	local qty = npcParseBuyQuantity(msg, maxQty)

	-- YUR CHANGE (Dark Rodo audit 2026-06-30): pre-check backpack space
	-- before showing the buy prompt. Saves the player a "yes" roundtrip
	-- for purchases that would fail anyway. The C++ side already handles
	-- partial delivery + refund, but UX-wise it's nicer to skip the prompt.
	local free = getPlayerFreeSlots(cid)
	if free < qty then
		selfSay('You do not have enough space in your backpack for that. Free up some slots first.')
		return false
	end

	if entry.fluidSubtype ~= nil then
		buyFluidQty(cid, entry.itemid, entry.fluidSubtype, qty, entry.unitPrice * qty)
	elseif entry.runeCharges ~= nil then
		buyRuneQty(cid, entry.itemid, qty, entry.runeCharges, entry.unitPrice * qty)
	elseif entry.itemQuantity ~= nil then
		buyItemQty(cid, entry.itemid, qty, entry.unitPrice * qty)
	else
		buy(cid, entry.itemid, qty, entry.unitPrice * qty)
	end
	return true
end

function npcTryCatalogSell(cid, msg, entries)
	local entry = npcFindCatalogEntry(msg, entries)
	if entry then
		sell(cid, entry.itemid, entry.count or 1, entry.price)
		return true
	end

	return false
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
