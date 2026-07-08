-- simple quests based on uniqueId
-- to make quest create chest on map and set its uniqueId to id of quest item
-- vanilla items: uniqueId 1001-4999 (prize id = uniqueId)
-- zagan custom items: uniqueId 20100-20199 (prize id = uniqueId)

local function isQuestPrizeId(prize)
	return (prize > 1000 and prize < 5000) or (prize >= 20100 and prize <= 20199)
end

function onUse(cid, item, frompos, item2, topos)
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
