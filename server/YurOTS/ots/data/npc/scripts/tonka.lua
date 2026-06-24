focus = 0
talk_start = 0
target = 0
following = false
attacking = false

EXCHANGES = {
	{keys = {'ruby', 'small ruby'}, small = 2147, big = 2156, smallName = 'small ruby', bigName = 'big ruby'},
	{keys = {'emerald', 'small emerald'}, small = 2149, big = 2155, smallName = 'small emerald', bigName = 'big emerald'},
	{keys = {'amethyst', 'small amethyst'}, small = 2150, big = 2153, smallName = 'small amethyst', bigName = 'violet gem'},
	{keys = {'sapphire', 'small sapphire'}, small = 2146, big = 2154, smallName = 'small sapphire', bigName = 'yellow gem'},
	{keys = {'diamond', 'small diamond'}, small = 2145, big = 2158, smallName = 'small diamond', bigName = 'blue gem'}
}

NEED = 20

function onThingMove(creature, thing, oldpos, oldstackpos)
end

function onCreatureAppear(creature)
end

function onCreatureDisappear(cid, pos)
	npcOnCreatureDisappear(cid)
end

function onCreatureTurn(creature)
end

function showExchangeList()
	selfSay('I fuse gems: 20 small for 1 big. Same color family.')
	selfSay('Ruby, emerald, amethyst, sapphire or diamond. Say exchange ruby, etc.')
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
	local have = getPlayerItemCount(cid, ex.small)
	if have < NEED then
		selfSay('You need ' .. NEED .. ' ' .. ex.smallName .. '. You have ' .. have .. '.')
		return
	end

	if doPlayerRemoveItem(cid, ex.small, NEED) == -1 then
		selfSay('Something went wrong. Try again.')
		return
	end

	if doPlayerAddItem(cid, ex.big, 1) == -1 then
		doPlayerAddItem(cid, ex.small, NEED)
		selfSay('You have no room. Free some space first.')
		return
	end

	selfSay('Done! Here is your ' .. ex.bigName .. '.')
end

function onCreatureSay(cid, type, msg)
	msg = string.lower(msg)

	local state = npcHandleMessage(
		cid,
		msg,
		'Hello ' .. creatureGetName(cid) .. '! I upgrade small gems into big ones. Say exchange for details.',
		'One moment, ' .. creatureGetName(cid) .. '.'
	)
	if state ~= 'focused' then
		return
	end

	if msgcontains(msg, 'exchange') or msgcontains(msg, 'trade') or msgcontains(msg, 'help')
		or msgcontains(msg, 'offer') or msgcontains(msg, 'list') then
		showExchangeList()
	elseif msgcontains(msg, 'change') or msgcontains(msg, 'fuse') or msgcontains(msg, 'upgrade') then
		local ex = matchExchange(msg)
		if ex then
			doExchange(cid, ex)
		else
			showExchangeList()
		end
	else
		local ex = matchExchange(msg)
		if ex then
			doExchange(cid, ex)
		end
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink(30, 'Next please...')
end
