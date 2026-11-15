-- Read/write items + training bonus parchment (1953 at 135 130 9).

local TRAINING_BONUS_ITEM = 1953
local TRAINING_BONUS_POS = {x = 135, y = 130, z = 9}
local STORAGE_BONUS_DATE = 9102
local STORAGE_BONUS_MINUTES = 9103
local BONUS_MINUTES = 300

local function trainingToday()
	local t = os.date("*t")
	return t.year * 10000 + t.month * 100 + t.day
end

local function isTrainingBonusParchment(item, frompos)
	return item.itemid == TRAINING_BONUS_ITEM
		and frompos.x == TRAINING_BONUS_POS.x
		and frompos.y == TRAINING_BONUS_POS.y
		and frompos.z == TRAINING_BONUS_POS.z
end

local function tryClaimTrainingBonus(cid)
	local today = trainingToday()
	local claimedDate = getPlayerStorageValue(cid, STORAGE_BONUS_DATE)

	if claimedDate == today then
		doPlayerSendTextMessage(cid, 22,
			"The parchment is empty. You have already claimed your +5 hours of training for today.")
		return 1
	end

	setPlayerStorageValue(cid, STORAGE_BONUS_DATE, today)
	setPlayerStorageValue(cid, STORAGE_BONUS_MINUTES, BONUS_MINUTES)
	doPlayerSendTextMessage(cid, 22,
		"The parchment blesses your training. You received +5 hours of training time for today.")
	doSendMagicEffect(getPlayerPosition(cid), 13)
	return 1
end

function onUse(cid, item, frompos, item2, topos)
	if isTrainingBonusParchment(item, frompos) then
		return tryClaimTrainingBonus(cid)
	end

	-- getItemRWInfo: bit 1 = se puede leer, bit 2 = se puede escribir. (Antes usaba "rw and 1",
	-- que en Lua siempre es verdadero, y abría como editables hasta los libros de solo lectura.)
	local rw = getItemRWInfo(item.uid) or 0
	if rw < 0 then
		rw = 0
	end
	if math.floor(rw / 2) % 2 == 1 then
		doShowTextWindow(item.uid, 100, 1)
	elseif rw % 2 == 1 or item.itemid == 2598 then
		doShowTextWindow(item.uid, 0, 0)
	end

	return 1
end
