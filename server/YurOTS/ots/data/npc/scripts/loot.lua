focus = 0
talk_start = 0
target = 0
following = false
attacking = false

LOOT_OFFERS = {
	{keys = {'royal helmet'}, itemid = 2498, price = 20000},
	{keys = {'warrior helmet'}, itemid = 2475, price = 3000},
	{keys = {'crusader helmet'}, itemid = 2497, price = 3000},
	{keys = {'crown helmet'}, itemid = 2491, price = 2000},
	{keys = {'devil helmet'}, itemid = 2462, price = 2000},
	{keys = {'mystic turban'}, itemid = 2663, price = 500},
	{keys = {'chain helmet'}, itemid = 2458, price = 35},
	{keys = {'iron helmet'}, itemid = 2459, price = 30},
	{keys = {'steel boots'}, itemid = 2645, price = 20000},
	{keys = {'boh', 'boots of haste'}, itemid = 2195, price = 4000},
	{keys = {'magic plate armor', 'mpa'}, itemid = 2472, price = 100000},
	{keys = {'dragon scale mail', 'dsm'}, itemid = 2492, price = 30000},
	{keys = {'golden armor'}, itemid = 2466, price = 10000},
	{keys = {'crown armor'}, itemid = 2487, price = 5000},
	{keys = {'knight armor'}, itemid = 2476, price = 3000},
	{keys = {'blue robe'}, itemid = 2656, price = 3000},
	{keys = {'lady armor'}, itemid = 2500, price = 1000},
	{keys = {'plate armor'}, itemid = 2463, price = 300},
	{keys = {'brass armor'}, itemid = 2465, price = 200},
	{keys = {'chain armor'}, itemid = 2464, price = 100},
	{keys = {'golden legs'}, itemid = 2470, price = 80000},
	{keys = {'crown legs'}, itemid = 2488, price = 5000},
	{keys = {'knight legs'}, itemid = 2477, price = 3000},
	{keys = {'plate legs'}, itemid = 2647, price = 500},
	{keys = {'brass legs'}, itemid = 2478, price = 100},
	{keys = {'chain legs'}, itemid = 2478, price = 50},
	{keys = {'shield of the mastermind', 'mms'}, itemid = 2514, price = 80000},
	{keys = {'demon shield'}, itemid = 2520, price = 40000},
	{keys = {'vampire shield'}, itemid = 2534, price = 4000},
	{keys = {'medusa shield'}, itemid = 2536, price = 3500},
	{keys = {'amazon shield'}, itemid = 2537, price = 3000},
	{keys = {'crown shield'}, itemid = 2519, price = 2000},
	{keys = {'tower shield'}, itemid = 2528, price = 2000},
	{keys = {'dragon shield'}, itemid = 2516, price = 1500},
	{keys = {'guardian shield'}, itemid = 2515, price = 1200},
	{keys = {'beholder shield'}, itemid = 2518, price = 1000},
	{keys = {'dwarven shield'}, itemid = 2525, price = 100},
	{keys = {'giant sword'}, itemid = 2393, price = 10000},
	{keys = {'bright sword'}, itemid = 2407, price = 6000},
	{keys = {'ice rapier'}, itemid = 2396, price = 4000},
	{keys = {'fire sword'}, itemid = 2392, price = 3000},
	{keys = {'serpent sword'}, itemid = 2409, price = 1500},
	{keys = {'spike sword'}, itemid = 2383, price = 800},
	{keys = {'two handed sword'}, itemid = 2377, price = 400},
	{keys = {'broad sword'}, itemid = 2413, price = 70},
	{keys = {'short sword'}, itemid = 2406, price = 30},
	{keys = {'sabre'}, itemid = 2385, price = 25},
	{keys = {'sword'}, itemid = 2376, price = 25},
	{keys = {'dragon lance'}, itemid = 2414, price = 10000},
	{keys = {'fire axe'}, itemid = 2432, price = 10000},
	{keys = {'knight axe'}, itemid = 2430, price = 2000},
	{keys = {'double axe'}, itemid = 2387, price = 200},
	{keys = {'halberd'}, itemid = 2381, price = 200},
	{keys = {'battle axe'}, itemid = 2378, price = 100},
	{keys = {'hatchet'}, itemid = 2388, price = 20},
	{keys = {'war hammer'}, itemid = 2391, price = 4000},
	{keys = {'skull staff'}, itemid = 2436, price = 4000},
	{keys = {'dragon hammer'}, itemid = 2434, price = 2000},
	{keys = {'clerical mace'}, itemid = 2423, price = 200},
	{keys = {'battle hammer'}, itemid = 2417, price = 60},
	{keys = {'mace'}, itemid = 2398, price = 30},
	{keys = {'platinum amulet'}, itemid = 2171, price = 2000},
	{keys = {'scarf'}, itemid = 2661, price = 500}
}

LOOT_TOPICS = {
	{keys = {'helmets'}, reply = 'I buy royal (20k), warrior (3k), crusader (3k), crown (2k), devil (2k), chain (35gp) and iron helmets (30gp), also mystic turbans (500gp).'},
	{keys = {'boots'}, reply = 'I buy steel boots (20k) and boots of haste (4k).'},
	{keys = {'armors'}, reply = 'I buy golden (10k), crown (5k), knight (3k), lady (1k), plate (300gp), brass (200gp) and chain armors (100gp), also mpa (100k), dsm (30k) and blue robes (3k).'},
	{keys = {'legs'}, reply = 'I buy golden (80k), crown (5k), knight (3k), plate (500gp), brass (100gp) and chain legs (50gp).'},
	{keys = {'shields'}, reply = 'I buy demon (40k), vampire (4k), medusa (3.5k), amazon (3k), crown (2k), tower (2k), dragon (1.5k), guardian (1.2k), beholder (1k), and dwarven shields (100gp), also mms (80k)'},
	{keys = {'swords'}, reply = 'I buy giant (10k), bright (6k), fire (3k) serpent (1.5k), spike (800gp) and two handed swords (400gp), also ice rapiers (4k), broad swords (70gp), short swords (30gp), sabres (25gp) and swords (25gp).'},
	{keys = {'axes'}, reply = 'I buy fire (10k), knight (2k), double (200gp) and battle axes (100gp), also dragon lances (10k), halberds (200gp) and hatchets (20gp).'},
	{keys = {'clubs'}, reply = 'I buy war (4k), dragon (2k) and battle hammers (60gp), also skull staffs (4k) and clerical maces (200gp).'},
	{keys = {'amulets'}, reply = 'I buy platinum amulets (2k) and scarfs (500gp).'}
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
