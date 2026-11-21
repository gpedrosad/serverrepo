-- Regalos de nivel: una caja por cada nivel nuevo (la da player.cpp, Player::onLevelAdvance).
-- Al usarla se abre: sale oro, un ítem o, con suerte, un raro que se anuncia a todo el server.
-- Cada rango de nivel tiene su caja (server ids 20354-20359) y su tabla; desde el 50 son mejores.
-- Doc: docs/gameplay/LEVEL_UP_REWARDS.md

local MSG_ADVANCE = 19        -- blanco, centro de la pantalla
local MSG_EVENT = 20          -- blanco, abajo
local EFFECT_OPEN = 12        -- NM_ME_MAGIC_ENERGIE
local EFFECT_RARE = 50        -- NM_ME_LEVEL_UP

-- rare / item: probabilidad en % (lo que queda es oro). gold = {mínimo, máximo} en gp.
local GIFTS = {
	[20354] = { -- novice gift, niveles 2-19
		rare = 1, item = 30, gold = {30, 150},
		items = {2460, 2465, 2478, 2509, 2398, 2376, 2380, 2643, 2457, 2513},
		rares = {2476, 2516, 2392},
	},
	[20355] = { -- adventurer gift, 20-34
		rare = 2, item = 30, gold = {200, 600},
		items = {2457, 2463, 2647, 2525, 2381, 2383, 2434, 2387, 2513, 2477},
		rares = {2475, 2392, 2432, 2195},
	},
	[20356] = { -- veteran gift, 35-49
		rare = 3, item = 30, gold = {500, 1500},
		items = {2475, 2476, 2477, 2516, 2392, 2432, 2436, 2491, 2414},
		rares = {2487, 2488, 2195, 2498},
	},
	[20357] = { -- champion gift, 50-79
		rare = 4, item = 35, gold = {1500, 4000},
		items = {2487, 2488, 2491, 2519, 2498, 2536, 2443, 2414},
		rares = {2492, 2195, 2400, 2421, 2466, 2514},
	},
	[20358] = { -- heroic gift, 80-99
		rare = 5, item = 35, gold = {3000, 8000},
		items = {2492, 2498, 2536, 2514, 2195, 2470, 2519},
		rares = {2472, 2466, 2400, 2421},
	},
	[20359] = { -- legendary gift, 100+
		rare = 6, item = 35, gold = {6000, 15000},
		items = {2470, 2466, 2514, 2195, 2492, 2400},
		rares = {2472, 2421, 2522, 2415},
	},
}

local function addMoney(cid, amount)
	local coins = {{2160, 10000}, {2152, 100}, {2148, 1}}
	for _, coin in ipairs(coins) do
		local n = math.floor(amount / coin[2])
		amount = amount - n * coin[2]
		while n > 0 do
			local stack = math.min(n, 100)
			doPlayerAddItem(cid, coin[1], stack)
			n = n - stack
		end
	end
end

math.randomseed(os.time())

local function withArticle(name)
	-- plurales sin artículo: "boots of haste", "plate legs"
	if string.find(name, "^boots") or string.find(name, "boots$") or string.find(name, "legs$") then
		return name
	end
	if string.find(name, "^[aeiouAEIOU]") then
		return "an " .. name
	end
	return "a " .. name
end

local function pick(list)
	return list[math.random(1, table.getn(list))]
end

function onUse(cid, item, frompos, item2, topos)
	local gift = GIFTS[item.itemid]
	if gift == nil then
		return 0
	end
	local giftName = withArticle(getItemName(item.itemid))
	local pos = getPlayerPosition(cid)
	doRemoveItem(item.uid, 1)

	local roll = math.random(1, 100)
	if roll <= gift.rare then
		local id = pick(gift.rares)
		local name = withArticle(getItemName(id))
		doPlayerAddItem(cid, id, 1)
		doSendMagicEffect(pos, EFFECT_RARE)
		-- a todos, también al que lo abrió
		doBroadcastMessage(MSG_ADVANCE, getPlayerName(cid) .. " opened " .. giftName .. " and found " .. name .. "!")
	elseif roll <= gift.rare + gift.item then
		local id = pick(gift.items)
		doPlayerAddItem(cid, id, 1)
		doSendMagicEffect(pos, EFFECT_OPEN)
		doPlayerSendTextMessage(cid, MSG_EVENT, "You opened " .. giftName .. " and found " .. withArticle(getItemName(id)) .. ".")
	else
		local amount = math.random(gift.gold[1], gift.gold[2])
		addMoney(cid, amount)
		doSendMagicEffect(pos, EFFECT_OPEN)
		doPlayerSendTextMessage(cid, MSG_EVENT, "You opened " .. giftName .. " and found " .. amount .. " gold.")
	end
	return 1
end
