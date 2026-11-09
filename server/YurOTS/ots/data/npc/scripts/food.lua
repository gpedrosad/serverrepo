-- Lector (comida). Tienda simple: todo a 8gp, acepta cantidad ("5 ham").

FOOD_HELP = 'Everything is 8gp: ham, meat, carrot, apple, brown bread, brown mushroom and egg. Say any amount, e.g. "5 ham".'

FOOD_BUYS = {
	{keys = {'brown bread', 'bread'}, itemid = 2691, unitPrice = 8},
	{keys = {'brown mushroom', 'mushroom'}, itemid = 2789, unitPrice = 8},
	{keys = {'ham'}, itemid = 2671, unitPrice = 8},
	{keys = {'carrot'}, itemid = 2684, unitPrice = 8},
	{keys = {'meat'}, itemid = 2666, unitPrice = 8},
	{keys = {'apple'}, itemid = 2674, unitPrice = 8},
	{keys = {'egg'}, itemid = 2695, unitPrice = 8},
}

npcDefine{
	greet = function(cid) return 'Hi ' .. creatureGetName(cid) .. '! ' .. FOOD_HELP end,
	onMessage = npcCatalogHandler{help = FOOD_HELP, buys = FOOD_BUYS},
}
