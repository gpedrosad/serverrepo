-- Fargum y Nimral (barco): viajes pagos a destinos fijos, con confirmación.
-- Script compartido por todos los barqueros. Viajar no cambia el temple del jugador.
talk_state = 0
pending_travel = nil

EPSTEIN = 'Epstein Island' -- isla de caza; ya no es Rookgaard ni tiene restricción de vocación

-- dest = sqm exacto de llegada.
TRAVELS = {
	{keys = {'elfland', 'elf land'}, price = 20, dest = {111, 60, 6}, name = 'Elfland'},
	{keys = {'epstein island', 'epstein'}, price = 20, dest = {85, 209, 7}, name = EPSTEIN},
	{keys = {'hell quest', 'hell'}, price = 20, dest = {345, 211, 7}, name = 'Hell Quest'},
	{keys = {'dragon land'}, price = 50, dest = {121, 118, 7}, name = 'Dragon Land'},
	{keys = {'frozen isle', 'frozen', 'isla helada', 'hielo'}, price = 20, dest = {395, 104, 7}, name = 'Frozen Isle'},
	{keys = {'gauntlet'}, price = 20, dest = {452, 41, 7}, name = 'Gauntlet'},
	{keys = {'city', 'the city'}, price = 20, dest = {172, 65, 7}, name = 'The City'},
}

-- Personal del server: los nombres que empiezan con "GM" (la web no deja crear jugadores así, ver
-- web/data.py). Los GM viajan gratis a cualquier destino.
local function isStaff(cid)
	local name = creatureGetName(cid) or ''
	return string.lower(string.sub(name, 1, 2)) == 'gm'
end

-- Destinos: todos los jugadores pueden viajar a cualquier destino, incluida Epstein Island.
local function summary(cid, sep, withPrice)
	local parts = {}
	for i = 1, table.getn(TRAVELS) do
		table.insert(parts, withPrice(TRAVELS[i]))
	end
	return table.concat(parts, sep)
end

-- Ya está en ese muelle (cerca del punto de llegada, mismo piso): no se cobra por moverse un sqm.
local function isAlreadyThere(cid, travel)
	local x, y, z = creatureGetPosition(cid)
	return x ~= nil and z == travel.dest[3]
		and math.abs(x - travel.dest[1]) <= 6 and math.abs(y - travel.dest[2]) <= 6
end

-- Motivo por el que no puede viajar, o nil.
local function travelProblem(cid, travel)
	if isAlreadyThere(cid, travel) then
		return 'You are already in ' .. travel.name .. '.'
	end
	if isPzLocked(cid) then
		return 'You are in a fight! Calm down before you board.'
	end
	return nil
end

local function offerTravel(cid, travel)
	local problem = travelProblem(cid, travel)
	if problem then
		selfSay(problem)
		return
	end
	pending_travel = travel
	talk_state = 1
	selfSay('A trip to ' .. travel.name .. ' costs ' .. travel.price .. 'gp. Ready to go? (yes or si)')
end

local function doTravel(cid, travel)
	local problem = travelProblem(cid, travel) -- pudo cambiar desde la oferta (p. ej. entró en combate)
	if problem then
		selfSay(problem)
		return
	end
	if not isStaff(cid) and not pay(cid, travel.price) then   -- el personal viaja gratis (pruebas)
		selfSay('Sorry, you need ' .. travel.price .. ' gold for that trip.')
		return
	end
	cancelPendingTrade(cid)
	npcResetState()
	selfSay('All aboard! Enjoy the trip!')
	travelPlayerTo(cid, travel.dest[1], travel.dest[2], travel.dest[3])
end

local function onMessage(cid, msg)
	local travel = npcFindCatalogEntry(msg, TRAVELS)

	if talk_state == 1 then
		if travel and travel ~= pending_travel then -- cambió de destino: se ofrece el nuevo
			offerTravel(cid, travel)
			return
		end
		local chosen = pending_travel
		if npcHandlePendingYesNo(cid, msg, function() doTravel(cid, chosen) end) then
			talk_state = 0
			pending_travel = nil
		else
			selfSay('Please say yes or no.')
		end
		return
	end

	if npcIsHelp(msg) then
		selfSay(summary(cid, '. ', function(t) return t.name .. ': ' .. t.price .. 'gp' end) .. '. Just say where you want to go!')
	elseif travel then
		offerTravel(cid, travel)
	end
end

npcDefine{
	greet = function(cid)
		return 'Hi ' .. creatureGetName(cid) .. '! I sail to '
			.. summary(cid, ', ', function(t) return t.name .. ' (' .. t.price .. 'gp)' end) .. '. Where do you want to go?'
	end,
	busy = function(cid) return 'One moment, ' .. creatureGetName(cid) .. '!' end,
	state = {talk_state = 0, pending_travel = nil},
	onMessage = onMessage,
}
