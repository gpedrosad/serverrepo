-- Perac (arcos y munición). Tienda simple con cantidad ("50 arrows").

BOWS_HELP = 'Crossbow 200gp, bow 100gp, arrows 2gp each, bolts 3gp each, power bolts 8gp each, spears 10gp each. Say any amount, e.g. "50 arrows" or "3 power bolts".'

BOW_BUYS = {
	{keys = {'power bolt', 'power bolts'}, itemid = 2547, unitPrice = 8},
	{keys = {'crossbow'}, itemid = 2455, unitPrice = 200},
	{keys = {'bow'}, itemid = 2456, unitPrice = 100},
	{keys = {'arrow', 'arrows'}, itemid = 2544, unitPrice = 2},
	{keys = {'bolt', 'bolts'}, itemid = 2543, unitPrice = 3},
	{keys = {'spear', 'spears'}, itemid = 2389, unitPrice = 10},
}

npcDefine{
	greet = function(cid) return 'Hi ' .. creatureGetName(cid) .. '! ' .. BOWS_HELP end,
	onMessage = npcCatalogHandler{help = BOWS_HELP, helpKeys = {'distance', 'ammo', 'ammunition'}, buys = BOW_BUYS},
}
