-- Experience recovery rune (20131): restores 60-80% of exp lost on the last death.

local EXPERIENCE_RECOVERY_RUNE = 20131
local STORAGE_LAST_DEATH_LOST_EXP = 9110

function onUse(cid, item, frompos, item2, topos)
	if item.itemid ~= EXPERIENCE_RECOVERY_RUNE then
		return 0
	end

	local lostExp = getPlayerStorageValue(cid, STORAGE_LAST_DEATH_LOST_EXP)
	if lostExp == nil or lostExp < 1 then
		doPlayerSendCancel(cid, "This rune has no death experience to restore.")
		return 1
	end

	local percent = math.random(60, 80)
	local recovered = math.floor(lostExp * percent / 100)
	if recovered < 1 then
		doPlayerSendCancel(cid, "The lost experience is too small to recover.")
		return 1
	end

	doPlayerAddExp(cid, recovered)
	setPlayerStorageValue(cid, STORAGE_LAST_DEATH_LOST_EXP, 0)
	doRemoveItem(item.uid, 1)

	doPlayerSendTextMessage(cid, 22,
		"You recovered " .. recovered .. " experience (" .. percent .. "% of your last death).")
	doSendMagicEffect(getPlayerPosition(cid), 13)
	return 1
end
