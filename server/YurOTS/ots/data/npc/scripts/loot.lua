focus = 0
talk_start = 0
target = 0
following = false
attacking = false

LOOT_OFFERS = {
	{keys = {'royal helmet'}, itemid = 2498, price = 30000},
	{keys = {'warrior helmet'}, itemid = 2475, price = 5000},
	{keys = {'crusader helmet'}, itemid = 2497, price = 6000},
	{keys = {'crown helmet'}, itemid = 2491, price = 2500},
	{keys = {'devil helmet'}, itemid = 2462, price = 2000},
	{keys = {'mystic turban'}, itemid = 2663, price = 500},
	{keys = {'chain helmet'}, itemid = 2458, price = 50},
	{keys = {'iron helmet'}, itemid = 2459, price = 150},
	{keys = {'steel boots'}, itemid = 2645, price = 30000},
	{keys = {'boh', 'boots of haste'}, itemid = 2195, price = 30000},
	{keys = {'magic plate armor', 'mpa'}, itemid = 2472, price = 100000},
	{keys = {'dragon scale mail', 'dsm'}, itemid = 2492, price = 40000},
	{keys = {'golden armor'}, itemid = 2466, price = 20000},
	{keys = {'crown armor'}, itemid = 2487, price = 12000},
	{keys = {'knight armor'}, itemid = 2476, price = 4500},
	{keys = {'blue robe'}, itemid = 2656, price = 10000},
	{keys = {'lady armor'}, itemid = 2500, price = 1500},
	{keys = {'plate armor'}, itemid = 2463, price = 500},
	{keys = {'brass armor'}, itemid = 2465, price = 300},
	{keys = {'chain armor'}, itemid = 2464, price = 150},
	{keys = {'golden legs'}, itemid = 2470, price = 80000},
	{keys = {'crown legs'}, itemid = 2488, price = 12000},
	{keys = {'knight legs'}, itemid = 2477, price = 4500},
	{keys = {'plate legs'}, itemid = 2647, price = 700},
	{keys = {'brass legs'}, itemid = 2478, price = 200},
	{keys = {'chain legs'}, itemid = 2547, price = 100},
	{keys = {'shield of the mastermind', 'mms'}, itemid = 2514, price = 80000},
	{keys = {'demon shield'}, itemid = 2520, price = 40000},
	{keys = {'vampire shield'}, itemid = 2534, price = 15000},
	{keys = {'medusa shield'}, itemid = 2536, price = 9000},
	{keys = {'amazon shield'}, itemid = 2537, price = 4000},
	{keys = {'crown shield'}, itemid = 2519, price = 8000},
	{keys = {'tower shield'}, itemid = 2528, price = 8000},
	{keys = {'dragon shield'}, itemid = 2516, price = 4000},
	{keys = {'guardian shield'}, itemid = 2515, price = 2000},
	{keys = {'beholder shield'}, itemid = 2518, price = 1500},
	{keys = {'dwarven shield'}, itemid = 2525, price = 200},
	{keys = {'giant sword'}, itemid = 2393, price = 17000},
	{keys = {'bright sword'}, itemid = 2407, price = 7000},
	{keys = {'ice rapier'}, itemid = 2396, price = 5000},
	{keys = {'fire sword'}, itemid = 2392, price = 4000},
	{keys = {'serpent sword'}, itemid = 2409, price = 2500},
	{keys = {'spike sword'}, itemid = 2383, price = 1200},
	{keys = {'two handed sword'}, itemid = 2377, price = 600},
	{keys = {'broad sword'}, itemid = 2413, price = 500},
	{keys = {'short sword'}, itemid = 2406, price = 60},
	{keys = {'sabre'}, itemid = 2385, price = 50},
	{keys = {'sword'}, itemid = 2376, price = 50},
	{keys = {'dragon lance'}, itemid = 2414, price = 10000},
	{keys = {'fire axe'}, itemid = 2432, price = 10000},
	{keys = {'knight axe'}, itemid = 2430, price = 3000},
	{keys = {'double axe'}, itemid = 2387, price = 300},
	{keys = {'halberd'}, itemid = 2381, price = 400},
	{keys = {'battle axe'}, itemid = 2378, price = 200},
	{keys = {'hatchet'}, itemid = 2388, price = 40},
	{keys = {'war hammer'}, itemid = 2391, price = 5000},
	{keys = {'skull staff'}, itemid = 2436, price = 6000},
	{keys = {'dragon hammer'}, itemid = 2434, price = 3000},
	{keys = {'clerical mace'}, itemid = 2423, price = 300},
	{keys = {'battle hammer'}, itemid = 2417, price = 120},
	{keys = {'mace'}, itemid = 2398, price = 50},
	{keys = {'platinum amulet'}, itemid = 2171, price = 2500},
	{keys = {'scarf'}, itemid = 2661, price = 600}
}

LOOT_TOPICS = {
	{keys = {'helmets'}, reply = 'I buy royal (30k), warrior (5k), crusader (6k), crown (2.5k), devil (2k), mystic turbans (500gp), chain (50gp) and iron helmets (150gp).'},
	{keys = {'boots'}, reply = 'I buy steel boots (30k) and boots of haste (30k).'},
	{keys = {'armors'}, reply = 'I buy mpa (100k), dsm (40k), golden (20k), crown (12k), blue robe (10k), knight (4.5k), lady (1.5k), plate (500gp), brass (300gp) and chain armors (150gp).'},
	{keys = {'legs'}, reply = 'I buy golden (80k), crown (12k), knight (4.5k), plate (700gp), brass (200gp) and chain legs (100gp).'},
	{keys = {'shields'}, reply = 'I buy mms (80k), demon (40k), vampire (15k), medusa (9k), crown (8k), tower (8k), amazon (4k), dragon (4k), guardian (2k), beholder (1.5k) and dwarven shields (200gp).'},
	{keys = {'swords'}, reply = 'I buy giant (17k), bright (7k), fire (4k), ice rapiers (5k), serpent (2.5k), spike (1.2k) and two handed swords (600gp), also broad swords (500gp), short swords (60gp), sabres (50gp) and swords (50gp).'},
	{keys = {'axes'}, reply = 'I buy fire (10k), dragon lances (10k), knight (3k), double (300gp), halberds (400gp), battle (200gp) and hatchets (40gp).'},
	{keys = {'clubs'}, reply = 'I buy war (5k), skull staffs (6k), dragon (3k) and battle hammers (120gp), also clerical maces (300gp) and maces (50gp).'},
	{keys = {'amulets'}, reply = 'I buy platinum amulets (2.5k) and scarfs (600gp).'}
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

function onCreatureSay(cid, type, msg)
	msg = string.lower(msg)

	local state = npcHandleMessage(
		cid,
		msg,
		'Hi ' .. creatureGetName(cid) .. '! I buy weapons and armor. Say a item name to sell, or "helmets", "armors", "shields" and so on for prices.'
	)
	if state ~= 'focused' then
		return
	end

	if npcIsHelp(msg) then
		selfSay('Say helmets, boots, armors, legs, shields, swords, axes, clubs or amulets to see what I buy.')
		return
	end

	if npcTryCatalogSell(cid, msg, LOOT_OFFERS) then
		return
	end

	npcTryCatalogReply(msg, LOOT_TOPICS)
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
