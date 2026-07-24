-- Fish TP: usar fishing rod (2580) en el pozo del templo.
-- Splash + energy, teleports a la lagoon y spawnea mobs con efectos.
-- Textos ASCII (cliente 7.6).

FISH_HOLE = {x = 164, y = 54, z = 7}
LANDING = {x = 309, y = 392, z = 6}
LAGOON = {x0 = 300, y0 = 385, x1 = 318, y1 = 400, z = 6}

-- Efectos 7.6 (spells.lua): 1 splash/loose energy, 2 puff, 7 yellow rings,
-- 10 energy area, 11 energy damage, 20 poison cloud
FX_SPLASH = 1
FX_PUFF = 2
FX_RINGS = 7
FX_ENERGY = 10
FX_POP = 11
FX_CLOUD = 20

PACK = {
	{"Crab", 3},
	{"Crocodile", 2},
	{"Snake", 2},
	{"Tarantula", 1},
}

SPAWN_SPOTS = {
	{x = 307, y = 390, z = 6},
	{x = 311, y = 390, z = 6},
	{x = 305, y = 393, z = 6},
	{x = 313, y = 393, z = 6},
	{x = 307, y = 396, z = 6},
	{x = 311, y = 396, z = 6},
	{x = 309, y = 388, z = 6},
	{x = 309, y = 395, z = 6},
}

function fishTpIsHole(topos)
	return topos.x == FISH_HOLE.x and topos.y == FISH_HOLE.y and topos.z == FISH_HOLE.z
end

function fishTpCountCreatures()
	local count = 0
	local x, y
	for x = LAGOON.x0, LAGOON.x1 do
		for y = LAGOON.y0, LAGOON.y1 do
			local th = getThingfromPos({x = x, y = y, z = LAGOON.z, stackpos = 253})
			if th.itemid > 0 then
				count = count + 1
			end
		end
	end
	return count
end

function fishTpSpawnPack()
	-- Si ya hay pelea, no spamear packs
	if fishTpCountCreatures() > 2 then
		return 0
	end

	local spawned = 0
	local spot = 1
	local i, n, name
	for i = 1, table.getn(PACK) do
		name = PACK[i][1]
		for n = 1, PACK[i][2] do
			local pos = SPAWN_SPOTS[((spot - 1) % table.getn(SPAWN_SPOTS)) + 1]
			spot = spot + 1
			-- Animacion de "sale del agua": cloud → rings → pop → summon
			doSendMagicEffect(pos, FX_CLOUD)
			doSendMagicEffect(pos, FX_RINGS)
			if doSummonCreature(name, pos) ~= 0 then
				doSendMagicEffect(pos, FX_POP)
				doSendMagicEffect(pos, FX_ENERGY)
				spawned = spawned + 1
			else
				doSendMagicEffect(pos, FX_PUFF)
			end
		end
	end
	return spawned
end

-- Llamado desde fishing.lua. Devuelve true si consumio la action.
function fishTpTry(cid, topos)
	if not fishTpIsHole(topos) then
		return false
	end

	-- Splash en el pozo (misma animacion de pescar)
	doSendMagicEffect(topos, FX_SPLASH)
	doPlayerAddSkillTry(cid, 6, 1)

	local ppos = getPlayerPosition(cid)
	doSendMagicEffect(ppos, FX_RINGS)
	doSendMagicEffect(ppos, FX_POP)

	doPlayerSendTextMessage(cid, 22, "Something huge bites and pulls you under!")

	doTeleportThing(cid, LANDING)
	doSendMagicEffect(LANDING, FX_SPLASH)
	doSendMagicEffect(LANDING, FX_ENERGY)
	doSendMagicEffect(LANDING, FX_POP)

	local n = fishTpSpawnPack()
	if n > 0 then
		doPlayerSendTextMessage(cid, 22, "Creatures crawl out of the lagoon! (" .. n .. ")")
	else
		doPlayerSendTextMessage(cid, 22, "The lagoon is already restless. Clear it or wait.")
	end
	doPlayerSendTextMessage(cid, 22, "Exit: teleport south of the shore.")
	return true
end
