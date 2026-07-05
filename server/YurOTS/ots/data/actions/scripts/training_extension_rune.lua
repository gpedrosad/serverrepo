-- Training extension rune (20132): +12 hours of training for today (once per character per day).

local TRAINING_EXTENSION_RUNE = 20132
local STORAGE_BONUS_DATE = 9102
local STORAGE_BONUS_MINUTES = 9103
local STORAGE_TRAINING_EXTENSION_RUNE_DATE = 9104
local BONUS_MINUTES = 720

local function trainingToday()
	local t = os.date("*t")
	return t.year * 10000 + t.month * 100 + t.day
end

function onUse(cid, item, frompos, item2, topos)
	if item.itemid ~= TRAINING_EXTENSION_RUNE then
		return 0
	end

	local today = trainingToday()
	if getPlayerStorageValue(cid, STORAGE_TRAINING_EXTENSION_RUNE_DATE) == today then
		doPlayerSendTextMessage(cid, 22,
			"This training extension rune is spent. You already received +12 hours of training today.")
		return 1
	end

	local bonusDate = getPlayerStorageValue(cid, STORAGE_BONUS_DATE)
	local bonusMinutes = getPlayerStorageValue(cid, STORAGE_BONUS_MINUTES)
	if bonusDate ~= today or bonusMinutes < 0 then
		bonusMinutes = 0
	end

	setPlayerStorageValue(cid, STORAGE_BONUS_DATE, today)
	setPlayerStorageValue(cid, STORAGE_BONUS_MINUTES, bonusMinutes + BONUS_MINUTES)
	setPlayerStorageValue(cid, STORAGE_TRAINING_EXTENSION_RUNE_DATE, today)
	doRemoveItem(item.uid, 1)

	doPlayerSendTextMessage(cid, 22,
		"The training extension rune grants you +12 hours of training time for today.")
	doSendMagicEffect(getPlayerPosition(cid), 13)
	return 1
end
