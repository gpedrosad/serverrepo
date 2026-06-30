-- Premium scrolls: use on your character to activate account premium time.

local MSG_RED_TEXT = 25
local TEXTCOLOR_RED = 180
local EFFECT_PREMIUM = 13

local SCROLLS = {
	[1954] = { hours = 168, label = "1 semana" },
	[2345] = { hours = 336, label = "2 semanas" },
}

function onUse(cid, item, frompos, item2, topos)
	local cfg = SCROLLS[item.itemid]
	if not cfg then
		return 0
	end

	local pos = getPlayerPosition(cid)

	doRemoveItem(item.uid, 1)
	doAccountAddPremiumTime(cid, cfg.hours)
	doSendMagicEffect(pos, EFFECT_PREMIUM)
	doSendAnimatedText(pos, "Premium!", TEXTCOLOR_RED)
	doPlayerSendTextMessage(cid, MSG_RED_TEXT,
		"Felicitaciones! Premium activado: " .. cfg.label .. ". Usa !premmy para ver el tiempo restante.")
	return 1
end
