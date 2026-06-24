focus = 0
talk_start = 0
target = 0
following = false
attacking = false

GEMS = {
	{keys = {'big emerald'}, id = 2155, price = 10000, name = 'big emerald'},
	{keys = {'big ruby'}, id = 2156, price = 10000, name = 'big ruby'},
	{keys = {'gold nugget', 'nugget'}, id = 2157, price = 10000, name = 'gold nugget'},
	{keys = {'scarab coin', 'scarab'}, id = 2159, price = 100, name = 'scarab coin'},
	{keys = {'violet gem'}, id = 2153, price = 10000, name = 'violet gem'},
	{keys = {'yellow gem'}, id = 2154, price = 1000, name = 'yellow gem'},
	{keys = {'blue gem'}, id = 2158, price = 5000, name = 'blue gem'},
	{keys = {'small diamond', 'diamond'}, id = 2145, price = 300, name = 'small diamond'},
	{keys = {'small sapphire', 'sapphire'}, id = 2146, price = 250, name = 'small sapphire'},
	{keys = {'small ruby', 'ruby'}, id = 2147, price = 250, name = 'small ruby'},
	{keys = {'small emerald', 'emerald'}, id = 2149, price = 250, name = 'small emerald'},
	{keys = {'small amethyst', 'amethyst'}, id = 2150, price = 200, name = 'small amethyst'},
	{keys = {'talon'}, id = 2151, price = 320, name = 'talon'}
}

function onThingMove(creature, thing, oldpos, oldstackpos)
end

function onCreatureAppear(creature)
end

function onCreatureDisappear(cid, pos)
	npcOnCreatureDisappear(cid)
end

function onCreatureTurn(creature)
end

function showTradeList()
	selfSay('Small gems: amethyst 200gp, emerald/ruby/sapphire 250gp, diamond 300gp, talon 320gp.')
	selfSay('Rare: yellow 1k, blue 5k, violet 10k, big emerald/ruby 10k, gold nugget 10k, scarab coin 100gp.')
	selfSay('Say "sell ruby", "sell 3 amethyst" or "sell all". I will ask you to confirm.')
end

function parseSellCount(msg)
	local n = string.match(msg, 'sell%s+(%d+)') or string.match(msg, 'vender%s+(%d+)')
	if n then
		return tonumber(n)
	end
	n = string.match(msg, '^(%d+)%s')
	if n then
		return tonumber(n)
	end
	return 1
end

function normalizeSellMsg(msg)
	msg = string.gsub(msg, '^sell%s+', '')
	msg = string.gsub(msg, '^vender%s+', '')
	msg = string.gsub(msg, '^(%d+)%s+', '')
	return msg
end

function matchGem(msg)
	local text = normalizeSellMsg(msg)
	for i = 1, table.getn(GEMS) do
		local gem = GEMS[i]
		for j = 1, table.getn(gem.keys) do
			if msgcontains(text, gem.keys[j]) then
				return gem
			end
		end
	end
	return nil
end

function offerSell(cid, gem, msg)
	local count = parseSellCount(msg)
	if count < 1 then
		count = 1
	end

	local have = getPlayerItemCount(cid, gem.id)
	if have < 1 then
		selfSay('You do not have any ' .. gem.name .. '.')
		return
	end

	if count > have then
		selfSay('You only have ' .. have .. ' ' .. gem.name .. '.')
		return
	end

	sell(cid, gem.id, count, count * gem.price)
end

function sellAllGems(cid)
	local total = 0
	local parts = {}
	local bundle = {}
	local n = 0

	for i = 1, table.getn(GEMS) do
		local gem = GEMS[i]
		local cnt = getPlayerItemCount(cid, gem.id)
		if cnt > 0 then
			n = n + 1
			bundle[n] = {gem.id, cnt}
			total = total + (cnt * gem.price)
			parts[n] = cnt .. 'x ' .. gem.name
		end
	end

	if total < 1 then
		selfSay('You have no gems to sell.')
		return
	end

	sellBundle(cid, total, table.concat(parts, ', '), bundle)
end

function onCreatureSay(cid, type, msg)
	msg = string.lower(msg)

	local state = npcHandleMessage(
		cid,
		msg,
		'Hi ' .. creatureGetName(cid) .. '! I buy gems and diamonds. Say "list" for prices.'
	)
	if state ~= 'focused' then
		return
	end

	if npcIsHelp(msg) or msgcontains(msg, 'gems') then
		showTradeList()
	elseif msgcontains(msg, 'sell all') or msgcontains(msg, 'vender todo') or msgcontains(msg, 'all gems') then
		sellAllGems(cid)
	elseif msgcontains(msg, 'sell') or msgcontains(msg, 'vender') then
		local gem = matchGem(msg)
		if gem then
			offerSell(cid, gem, msg)
		else
			showTradeList()
		end
	else
		local gem = matchGem(msg)
		if gem then
			offerSell(cid, gem, msg)
		end
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
