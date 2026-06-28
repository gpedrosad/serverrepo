focus = 0
talk_start = 0
target = 0
following = false
attacking = false

FURNITURE_PRICE = 500

FURNITURE_OFFERS = {
	{keys = {'wooden chair'}, itemid = 3901},
	{keys = {'sofa chair'}, itemid = 3902},
	{keys = {'red cushioned chair'}, itemid = 3903},
	{keys = {'green cushioned chair'}, itemid = 3904},
	{keys = {'tusk chair'}, itemid = 3905},
	{keys = {'ivory chair'}, itemid = 3906},
	{keys = {'big table'}, itemid = 3909},
	{keys = {'square table'}, itemid = 3910},
	{keys = {'round table'}, itemid = 3911},
	{keys = {'small table'}, itemid = 3912},
	{keys = {'stone table'}, itemid = 3913},
	{keys = {'tusk table'}, itemid = 3914},
	{keys = {'bamboo table'}, itemid = 3919},
	{keys = {'pink flower'}, itemid = 3928},
	{keys = {'green flower'}, itemid = 3929},
	{keys = {'christmas tree'}, itemid = 3931},
	{keys = {'large trunk'}, itemid = 3938},
	{keys = {'drawer'}, itemid = 3921},
	{keys = {'dresser'}, itemid = 3932},
	{keys = {'locker'}, itemid = 3934},
	{keys = {'trough'}, itemid = 3935},
	{keys = {'box'}, itemid = 3915},
	{keys = {'coal basin'}, itemid = 3908},
	{keys = {'birdcage'}, itemid = 3918},
	{keys = {'harp'}, itemid = 3917},
	{keys = {'piano'}, itemid = 3926},
	{keys = {'globe'}, itemid = 3927},
	{keys = {'clock'}, itemid = 3933},
	{keys = {'lamp'}, itemid = 3937},
	{keys = {'blue tapestry'}, itemid = 1872},
	{keys = {'green tapestry'}, itemid = 1860},
	{keys = {'orange tapestry'}, itemid = 1866},
	{keys = {'pink tapestry'}, itemid = 1857},
	{keys = {'red tapestry'}, itemid = 1869},
	{keys = {'white tapestry'}, itemid = 1880},
	{keys = {'yellow tapestry'}, itemid = 1863},
	{keys = {'small purple pillow'}, itemid = 1678},
	{keys = {'small green pillow'}, itemid = 1679},
	{keys = {'small red pillow'}, itemid = 1680},
	{keys = {'small blue pillow'}, itemid = 1681},
	{keys = {'small orange pillow'}, itemid = 1682},
	{keys = {'small turquiose pillow'}, itemid = 1683},
	{keys = {'small white pillow'}, itemid = 1684},
	{keys = {'heart pillow'}, itemid = 1685},
	{keys = {'blue pillow'}, itemid = 1686},
	{keys = {'red pillow'}, itemid = 1687},
	{keys = {'green pillow'}, itemid = 1688},
	{keys = {'yellow pillow'}, itemid = 1689},
	{keys = {'round blue pillow'}, itemid = 1690},
	{keys = {'round red pillow'}, itemid = 1691},
	{keys = {'round purple pillow'}, itemid = 1692},
	{keys = {'round turquiose pillow'}, itemid = 1693}
}

FURNITURE_TOPICS = {
	{keys = {'chairs'}, reply = 'I sell wooden, sofa, red cushioned, green cushioned, tusk and ivory chairs.'},
	{keys = {'tables'}, reply = 'I sell big, square, round, small, stone, tusk, bamboo tables.'},
	{keys = {'plants'}, reply = 'I sell pink and green flowers, also christmas trees.'},
	{keys = {'containers'}, reply = 'I sell large trunks, boxes, drawers, dressers, lockers and troughs.'},
	{keys = {'more'}, reply = 'I sell coal basins, birdcages, harps, pianos, globes, clocks and lamps.'},
	{keys = {'tapestry', 'tapestries'}, reply = 'I sell blue, green, orange, pink, red, white and yellow tapestry.'},
	{keys = {'small'}, reply = 'I sell small purple, small green, small red, small blue, small orange, small turquiose and small white pillows.'},
	{keys = {'round'}, reply = 'I sell round blue, round red, round purple and round turquiose pillows.'},
	{keys = {'square'}, reply = 'I sell blue, red, green and yellow pillows.'},
	{keys = {'pillows'}, reply = 'I sell heart, small, sqare and round pillows.'}
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

function buyFurniture(cid, entry, msg)
	local qty = npcParseBuyQuantity(msg or '', 20)
	buy(cid, entry.itemid, qty, FURNITURE_PRICE * qty)
end

function onCreatureSay(cid, type, msg)
	msg = string.lower(msg)

	local state = npcHandleMessage(
		cid,
		msg,
		'Hi ' .. creatureGetName(cid) .. '! I sell furniture for your house — everything is 500gp each. Say "2 wooden chair" or any amount. Say "chairs", "tables", "pillows" or an item name.'
	)
	if state ~= 'focused' then
		return
	end

	if npcIsHelp(msg) then
		selfSay('Try chairs, tables, plants, containers, tapestries, pillows, small or round. Or say the exact item name!')
		return
	end

	local entry = npcFindCatalogEntry(msg, FURNITURE_OFFERS)
	if entry then
		buyFurniture(cid, entry, msg)
		return
	end

	npcTryCatalogReply(msg, FURNITURE_TOPICS)
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
