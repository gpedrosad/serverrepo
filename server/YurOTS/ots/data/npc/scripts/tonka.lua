-- Tonka (canje de gemas: 20 chicas del mismo tipo = 1 grande).
talk_state = 0
pending_exchange = nil

EXCHANGES = {
	{keys = {'ruby', 'small ruby'}, small = 2147, big = 2156, smallName = 'small rubies', bigName = 'big ruby'},
	{keys = {'emerald', 'small emerald'}, small = 2149, big = 2155, smallName = 'small emeralds', bigName = 'big emerald'},
	{keys = {'amethyst', 'small amethyst'}, small = 2150, big = 2153, smallName = 'small amethysts', bigName = 'violet gem'},
	{keys = {'sapphire', 'small sapphire'}, small = 2146, big = 2154, smallName = 'small sapphires', bigName = 'yellow gem'},
	{keys = {'diamond', 'small diamond'}, small = 2145, big = 2158, smallName = 'small diamonds', bigName = 'blue gem'}
}

NEED = 20

TONKA_HELP = 'I turn small gems into big gems. Strong monsters drop small gems — bring me 20 of the same type and I give you 1 big gem. Big gems can imbue gear: ruby on weapons, emerald on armor, violet on wands or rods, yellow on boots, blue on crystal arrows. Say "exchange" to start a trade.'

function showHelp()
	selfSay(TONKA_HELP)
	selfSay('Say "exchange ruby", "exchange emerald", "exchange amethyst", "exchange sapphire" or "exchange diamond".')
end

function showExchangeList()
	selfSay('Trade 20 small gems for 1 big gem of the same color.')
	selfSay('Say "exchange ruby", "exchange emerald", "exchange amethyst", "exchange sapphire" or "exchange diamond".')
end

function matchExchange(msg)
	return npcFindCatalogEntry(msg, EXCHANGES)
end

function addItemsExact(cid, itemid, count)
	for i = 1, count do
		if doPlayerAddItem(cid, itemid, 1) == -1 then
			return false, i - 1
		end
	end
	return true, count
end

function doExchange(cid, ex)
	if not ex then
		return
	end

	local have = getPlayerItemCount(cid, ex.small)
	if have < NEED then
		selfSay('You need ' .. NEED .. ' ' .. ex.smallName .. '. You have ' .. have .. '.')
		return
	end

	if doPlayerRemoveItem(cid, ex.small, NEED) == -1 then
		selfSay('You no longer have enough ' .. ex.smallName .. '.')
		return
	end

	if doPlayerAddItem(cid, ex.big, 1) == -1 then
		local restored, restoredCount = addItemsExact(cid, ex.small, NEED)
		if restored then
			selfSay('Something went wrong delivering your ' .. ex.bigName .. '. Your ' .. ex.smallName .. ' were returned.')
		else
			selfSay('Something went wrong delivering your ' .. ex.bigName .. ' and only ' .. restoredCount .. '/' .. NEED .. ' ' .. ex.smallName .. ' could be returned. Contact a GM.')
		end
		return
	end

	selfSay('Done! Here is your ' .. ex.bigName .. '.')
end

function offerExchange(cid, ex)
	local have = getPlayerItemCount(cid, ex.small)
	if have < NEED then
		selfSay('You need ' .. NEED .. ' ' .. ex.smallName .. '. You have ' .. have .. '.')
		return
	end

	pending_exchange = ex
	talk_state = 1
	selfSay('Trade ' .. NEED .. ' ' .. ex.smallName .. ' for 1 ' .. ex.bigName .. '? (yes or si)')
end

local function onMessage(cid, msg)
	if talk_state == 1 then
		if npcHandlePendingYesNo(cid, msg, function()
			doExchange(cid, pending_exchange)
		end) then
			talk_state = 0
			pending_exchange = nil
		end
		return
	end

	if msgcontains(msg, 'help') or msgcontains(msg, 'ayuda') then
		showHelp()
	elseif msgcontains(msg, 'exchange') or msgcontains(msg, 'cambiar') or msgcontains(msg, 'trade') then
		local ex = matchExchange(msg)
		if ex then
			offerExchange(cid, ex)
		else
			showExchangeList()
		end
	else
		local ex = matchExchange(msg)
		if ex then
			offerExchange(cid, ex)
		end
	end
end

npcDefine{
	greet = function(cid) return 'Hi ' .. creatureGetName(cid) .. '! I turn small gems into big ones. Say "help" or "exchange" to see what I do.' end,
	busy = function(cid) return 'One moment, ' .. creatureGetName(cid) .. '!' end,
	idleTimeout = 30,
	idleMessage = 'Next please...',
	onMessage = onMessage,
}
