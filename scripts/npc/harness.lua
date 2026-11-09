-- Banco de pruebas de NPCs: simula el servidor (API que npc.cpp registra) y corre un guion.
-- Uso (desde server/YurOTS/ots, con LuaJIT = mismo dialecto 5.1 que el server):
--   luajit ../../../scripts/npc/harness.lua data/npc/scripts/food.lua guion.txt
-- Imprime una transcripción determinista: SAY / CALL / ERROR por cada paso.
--
-- Guion (una orden por línea):
--   say <cid> <texto>      el jugador habla (onCreatureSay)
--   think [n]              n ticks de onThink (default 1)
--   advance <seg>          avanza el reloj virtual (os.clock / os.time)
--   near <cid> | far <cid> jugador al lado del NPC o lejos
--   pos <cid> <x> <y> <z>  posición exacta del jugador
--   set <cid> <campo> <n>  money, bank, level, items, slots, voc, premium, promoted, mana, guildstatus
--   disappear <cid>        onCreatureDisappear
--   # comentario

local script, scenario = arg[1], arg[2]

-- Lua 5.1 (Docker: liblua5.1) trae math.mod; LuaJIT no
math.mod = math.mod or math.fmod  -- solo para scripts viejos; los NPC ya usan math.fmod

-- reloj y azar deterministas -------------------------------------------------
local T0 = 1700000000
local now = T0
os.clock = function() return now - T0 end
os.time = function(t) if t then return 0 end return now end
local realdate = os.date
os.date = function(fmt, t) return realdate(fmt, t or now) end
local seed = 12345
math.randomseed = function() end
math.random = function(a, b)
	seed = (seed * 1103515245 + 12345) % 2147483648
	local r = seed / 2147483648
	if a == nil then return r end
	if b == nil then a, b = 1, a end
	return a + math.floor(r * (b - a + 1))
end

-- mundo simulado ---------------------------------------------------------------
local NPC_POS = {x = 100, y = 100, z = 7}
local players = {}
local function P(cid)
	cid = tonumber(cid) or 0
	if not players[cid] then
		players[cid] = {name = 'Player' .. cid, pos = {x = 101, y = 100, z = 7}, money = 100000, bank = 50000,
			level = 50, items = 10, slots = 20, voc = 1, premium = 1, promoted = 0, mana = 500,
			guildstatus = 0, guildname = '', storage = {}}
	end
	return players[cid]
end
local function byAny(x)  -- algunas funciones del C++ reciben el nombre, no el cid
	if type(x) == 'string' then
		for _, p in pairs(players) do if p.name == x then return p end end
		return {level = -1, guildstatus = 0, guildname = ''}
	end
	return P(x)
end
local creatures = 5000

local function fmt(v)
	local t = type(v)
	if t == 'string' then return string.format('%q', v) end
	if t == 'table' then
		local keys = {}
		for k in pairs(v) do keys[#keys + 1] = tostring(k) end
		table.sort(keys)
		local parts = {}
		for _, k in ipairs(keys) do parts[#parts + 1] = k .. '=' .. fmt(v[k] ~= nil and v[k] or v[tonumber(k)]) end
		return '{' .. table.concat(parts, ',') .. '}'
	end
	return tostring(v)
end
local function log(name, ...)
	local n = select('#', ...)
	local parts = {}
	for i = 1, n do parts[i] = fmt((select(i, ...))) end
	print('CALL ' .. name .. '(' .. table.concat(parts, ', ') .. ')')
end
local function api(name, ret)
	_G[name] = function(...)
		log(name, ...)
		if type(ret) == 'function' then return ret(...) end
		return ret
	end
end

selfSay = function(text) print('SAY ' .. tostring(text)) end
selfGetPosition = function() return NPC_POS.x, NPC_POS.y, NPC_POS.z end
creatureGetPosition = function(cid)
	local p = players[tonumber(cid) or -1]
	if not p then return nil end
	return p.pos.x, p.pos.y, p.pos.z
end
creatureGetName = function(cid) return P(cid).name end
creatureGetName2 = function(name) for cid, p in pairs(players) do if p.name == name then return cid end end return 0 end
for _, n in ipairs({'selfMove', 'selfMoveTo', 'selfAttackCreature', 'doPlayerSendTextMessage', 'buy', 'buyFluidBackpack',
	'buyFluidQty', 'buyRuneQty', 'buyItemQty', 'buyItemBackpack', 'sell', 'sellFluid', 'sellBundle',
	'travelPlayerTo', 'doSendMagicEffect', 'setPlayerMasterPos', 'doPlayerAddExp', 'learnSpell', 'setPlayerVocation',
	'setPlayerGuild', 'clearPlayerGuild', 'setPlayerGuildNick', 'setPlayerGuildTitle', 'setPlayerGuildStatus', 'doRemoveCreature'}) do
	api(n, nil)
end
api('cancelPendingTrade', true)
api('pay', function(cid, amount) local p = P(cid); if p.money >= (tonumber(amount) or 0) then p.money = p.money - amount; return true end return false end)
api('getPlayerStorageValue', function(cid, k) local v = P(cid).storage[k]; if v == nil then return -1 end return v end)
api('setPlayerStorageValue', function(cid, k, v) P(cid).storage[k] = v end)
api('doPlayerRemoveItem', 1)
api('doPlayerAddItem', 1)
api('getPlayerLevel', function(name) return byAny(name).level end)
api('getPlayerItemCount', function(cid) return P(cid).items end)
api('getPlayerFreeSlots', function(cid) return P(cid).slots end)
api('getPlayerFluidCount', function(cid) return P(cid).items end)
api('getPlayerMoney', function(cid) return P(cid).money end)
api('getPlayerBankBalance', function(cid) return P(cid).bank end)
api('doPlayerDepositMoney', 0)
api('doPlayerWithdrawMoney', 0)
api('doPlayerTransferMoneyTo', 0)
api('doPlayerAddMoney', 1)
api('getPlayerVocation', function(cid) return P(cid).voc end)
api('doSummonCreature', function() creatures = creatures + 1; return creatures end)
api('getTopCreature', 0)
api('isMonster', function(cid) return (tonumber(cid) or 0) >= 5000 end)  -- boolean, como el C++
api('getPlayerMana', function(cid) return P(cid).mana end)
api('doPlayerAddMana', 1)
api('foundNewGuild', 1)
api('getPlayerGuildStatus', function(name) return byAny(name).guildstatus end)
api('getPlayerGuildName', function(name) return byAny(name).guildname end)
api('isPremium', function(cid) return P(cid).premium == 1 end)
api('isPromoted', function(cid) return P(cid).promoted == 1 end)

-- carga como npc.cpp: lib primero, después el script --------------------------
local function run(label, f, ...)
	local ok, err = pcall(f, ...)
	if not ok then
		err = tostring(err):gsub('^[^:]*:%d+: ', ''):gsub('%[string "[^"]*"%]:%d+: ', '')
		print('ERROR ' .. label .. ': ' .. err)
	end
end
run('load lib', dofile, 'data/npc/scripts/lib/npc.lua')
run('load script', dofile, script)

for line in io.lines(scenario) do
	local cmd, rest = line:match('^(%S+)%s*(.*)$')
	if cmd and cmd:sub(1, 1) ~= '#' then
		print('>> ' .. line)
		if cmd == 'say' then
			local cid, text = rest:match('^(%d+)%s+(.*)$')
			P(cid)
			if onCreatureSay then run('onCreatureSay', onCreatureSay, tonumber(cid), 1, text) end
		elseif cmd == 'think' then
			for _ = 1, tonumber(rest) or 1 do
				now = now + 1
				if onThink then run('onThink', onThink) end
			end
		elseif cmd == 'advance' then
			now = now + tonumber(rest)
		elseif cmd == 'near' then
			P(rest).pos = {x = 101, y = 100, z = 7}
		elseif cmd == 'far' then
			P(rest).pos = {x = 130, y = 100, z = 7}
		elseif cmd == 'pos' then
			local cid, x, y, z = rest:match('(%d+)%s+(%d+)%s+(%d+)%s+(%d+)')
			P(cid).pos = {x = tonumber(x), y = tonumber(y), z = tonumber(z)}
		elseif cmd == 'set' then
			local cid, field, val = rest:match('(%d+)%s+(%S+)%s+(%S+)')
			P(cid)[field] = tonumber(val) or val
		elseif cmd == 'disappear' then
			if onCreatureDisappear then run('onCreatureDisappear', onCreatureDisappear, tonumber(rest), P(rest).pos) end
		end
	end
end
