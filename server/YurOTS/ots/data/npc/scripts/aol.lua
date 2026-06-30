focus = 0
talk_start = 0
target = 0
following = false
attacking = false

AOL_PRICE = 50000
SCARF_PRICE = 1000

RINGS = {
	{keys = {'energy ring', 'energy'}, itemid = 2167, unitPrice = 3000},
	{keys = {'might ring', 'might'}, itemid = 2164, unitPrice = 7000},
	{keys = {'time ring', 'time'}, itemid = 2169, unitPrice = 2000},
	{keys = {'stealth ring', 'stealth'}, itemid = 2165, unitPrice = 4000},
	{keys = {'ring of healing', 'healing ring', 'healing'}, itemid = 2214, unitPrice = 2500},
	{keys = {'life ring', 'life'}, itemid = 2168, unitPrice = 1500},
	{keys = {'sword ring', 'sword'}, itemid = 2207, unitPrice = 1000},
	{keys = {'axe ring', 'axe'}, itemid = 2208, unitPrice = 1000},
	{keys = {'club ring', 'club'}, itemid = 2209, unitPrice = 1000},
}

RINGS_HELP = 'Energy ring 3k, might ring 7k, time ring 2k, stealth ring 4k, life ring 1.5k, ring of healing 2.5k, sword/axe/club ring 1k each. Say any amount, e.g. "2 life ring".'

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
	selfSay('Scarf: ' .. SCARF_PRICE .. 'gp. Amulet of loss (AOL): ' .. AOL_PRICE .. 'gp.')
	selfSay(RINGS_HELP)
end

function showRingPrices()
	selfSay(RINGS_HELP)
end

function onCreatureSay(cid, type, msg)
	msg = string.lower(msg)

	local state = npcHandleMessage(
		cid,
		msg,
		'Hi ' .. creatureGetName(cid) .. '! I sell rings, scarf (1k) and amulet of loss / AOL (50k). Say "rings" or "help" for prices.'
	)
	if state ~= 'focused' then
		return
	end

	if npcIsHelp(msg) then
		showHelp()
	elseif msgcontains(msg, 'rings') or msgcontains(msg, 'anillos') then
		showRingPrices()
	elseif msgcontains(msg, 'aol') or msgcontains(msg, 'amulet of loss') then
		buy(cid, 2173, 1, AOL_PRICE)
	elseif msgcontains(msg, 'scarf') then
		buy(cid, 2661, 1, SCARF_PRICE)
	elseif npcTryCatalogBuyQuantity(cid, msg, RINGS) then
		return
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
