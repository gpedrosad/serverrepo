focus = 0
talk_start = 0
target = 0
following = false
attacking = false
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

TONKA_HELP = 'I turn small gems into big gems. Strong monsters drop small gems — bring me 20 of the same type and I give you 1 big gem. Big gems can imbue gear: ruby on weapons, emerald on armor, violet on wands or rods, yellow on boots. Say "exchange" to start a trade.'

function onThingMove(creature, thing, oldpos, oldstackpos)
end

function onCreatureAppear(creature)
end

function onCreatureDisappear(cid, pos)
	npcOnCreatureDisappear(cid)
end

function onCreatureTurn(creature)
end

function showHelp()
	selfSay(TONKA_HELP)
	selfSay('Say "exchange ruby", "exchange emerald", "exchange amethyst", "exchange sapphire" or "exchange diamond".')
end

function showExchangeList()
	selfSay('Trade 20 small gems for 1 big gem of the same color.')
	selfSay('Say "exchange ruby", "exchange emerald", "exchange amethyst", "exchange sapphire" or "exchange diamond".')
end

function matchExchange(msg)
	for i = 1, table.getn(EXCHANGES) do
		local ex = EXCHANGES[i]
		for j = 1, table.getn(ex.keys) do
			if msgcontains(msg, ex.keys[j]) then
				return ex
			end
		end
	end
	return nil
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
		selfSay('Something went wrong. Please try again.')
		return
	end

	if doPlayerAddItem(cid, ex.big, 1) == -1 then
		doPlayerAddItem(cid, ex.small, NEED)
		selfSay('You need more free space in your backpack.')
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

function onCreatureSay(cid, type, msg)
	msg = string.lower(msg)

	local state = npcHandleMessage(
		cid,
		msg,
		'Hi ' .. creatureGetName(cid) .. '! I turn small gems into big ones. Say "help" or "exchange" to see what I do.',
		'One moment, ' .. creatureGetName(cid) .. '!'
	)
	if state ~= 'focused' then
		return
	end

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

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink(30, 'Next please...')
end
