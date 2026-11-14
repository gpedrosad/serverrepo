-- simple quests based on uniqueId
-- to make quest create chest on map and set its uniqueId to id of quest item
-- vanilla items: uniqueId 1001-4999 (prize id = uniqueId)
-- zagan custom items: uniqueId 20100-20199 (prize id = uniqueId)

local function isQuestPrizeId(prize)
	return (prize > 1000 and prize < 5000) or (prize >= 20100 and prize <= 20199)
end

-- BEGIN QUEST_LEVELS (scripts/map/protect-quest-chests.py)
local CHEST_LEVEL = {
	["73,93,10"] = 50,
	["89,80,8"] = 30,
	["97,28,3"] = 60,
	["103,28,3"] = 60,
	["106,63,4"] = 30,
	["106,65,4"] = 30,
	["106,67,4"] = 30,
	["128,62,6"] = 60,
	["128,62,7"] = 60,
	["139,141,6"] = 30,
	["145,136,9"] = 40,
	["156,42,9"] = 20,
	["156,43,9"] = 20,
	["162,152,9"] = 50,
	["182,117,9"] = 90,
	["198,121,11"] = 100,
	["200,121,11"] = 100,
	["202,121,11"] = 100,
	["203,40,7"] = 30,
	["204,121,11"] = 100,
	["205,166,9"] = 80,
	["207,166,9"] = 80,
	["209,166,9"] = 80,
	["214,148,8"] = 60,
	["217,72,8"] = 80,
	["228,198,8"] = 80,
	["231,126,9"] = 60,
	["242,22,8"] = 40,
	["242,78,7"] = 40,
	["257,114,7"] = 45,
	["343,137,9"] = 100,
	["345,137,9"] = 100,
	["348,137,9"] = 100,
	["350,137,9"] = 100,
	["369,63,7"] = 40,
	["373,95,7"] = 25,
	["393,17,9"] = 70,
	["397,17,9"] = 70,
	["450,77,7"] = 80,
	["450,79,7"] = 80,
}
-- END QUEST_LEVELS

function onUse(cid, item, frompos, item2, topos)
	local chest_key = topos.x .. "," .. topos.y .. "," .. topos.z
	local req_level = CHEST_LEVEL[chest_key]
	if req_level and getPlayerLevel(cid) < req_level then
		doPlayerSendTextMessage(cid,22,'You need level ' .. req_level .. ' to open this chest.')
		return 1
	end

	prize = item.uid

	if isQuestPrizeId(prize) then
		queststatus = getPlayerStorageValue(cid,prize)

		if queststatus == -1 then
			doPlayerSendTextMessage(cid,22,'You have found a ' .. getItemName(prize) .. '.')
			doPlayerAddItem(cid,prize,1)
			setPlayerStorageValue(cid,prize,1)
		else
			doPlayerSendTextMessage(cid,22,"It is empty.")
		end

		return 1
	else
		return 0
	end
end
