focus = 0
talk_start = 0
target = 0
following = false
attacking = false
talk_state = 0
pending_reward = nil

dofile('data/npc/scripts/lib/daily_task.lua')

HUNTMASTER_HELP = 'I post daily hunt contracts by level. Say "task" for today\'s 3 contracts, pick 1, 2 or 3, then hunt. Say "status" for progress, "reward" to claim gold or exp, and "streak" for your consecutive-day bonus.'

function onThingMove(creature, thing, oldpos, oldstackpos)
end

function onCreatureAppear(creature)
end

function onCreatureDisappear(cid, pos)
	npcOnCreatureDisappear(cid)
end

function onCreatureTurn(creature)
end

function onCreatureChangeOutfit(creature)
end

function playerLevel(cid)
	local name = creatureGetName(cid)
	local level = getPlayerLevel(name)
	if level == nil or level < 1 then
		return 1
	end
	return level
end

function fmtAmount(n)
	return tostring(n)
end

function describeOfferLine(offer)
	return offer.slot .. ') ' .. offer.count .. ' ' .. offer.name
		.. ' — ' .. fmtAmount(offer.gold) .. ' gp or ' .. fmtAmount(offer.exp) .. ' exp'
end

function sayOffers(cid)
	local level = playerLevel(cid)
	local state = dailyTaskStorage(cid, DAILY_STORAGE_STATE)
	local bracketIndex = dailyTaskStorage(cid, DAILY_STORAGE_BRACKET)
	local bracket = nil
	local ids = nil

	if state == DAILY_STATE_OFFER and bracketIndex >= 1 then
		bracket = DAILY_BRACKETS[bracketIndex]
	else
		local name = creatureGetName(cid)
		bracket, ids = dailyTaskGenerateOffers(cid, level, name)
	end

	selfSay('Today\'s contracts, ' .. bracket.label .. ':')
	local slot
	for slot = 1, 3 do
		local offer = dailyTaskGetOfferSlot(cid, slot)
		if offer then
			selfSay(describeOfferLine(offer))
		end
	end
	selfSay('Say 1, 2 or 3 to accept. You cannot reroll today.')
end

function sayStatus(cid)
	dailyTaskEnsureDay(cid)
	local state = dailyTaskStorage(cid, DAILY_STORAGE_STATE)

	if state == DAILY_STATE_CLAIMED then
		selfSay('You already claimed today\'s reward. Come back tomorrow for new contracts.')
		return
	end

	if state == DAILY_STATE_DONE then
		local monsterId = dailyTaskStorage(cid, DAILY_STORAGE_MONSTER)
		local name = dailyTaskMonsterName(monsterId) or 'monsters'
		local required = dailyTaskStorage(cid, DAILY_STORAGE_REQUIRED)
		selfSay('Contract complete: ' .. required .. '/' .. required .. ' ' .. name .. '. Say "reward" to choose gold or exp.')
		return
	end

	if state == DAILY_STATE_ACTIVE then
		local monsterId = dailyTaskStorage(cid, DAILY_STORAGE_MONSTER)
		local name = dailyTaskMonsterName(monsterId) or 'monsters'
		local required = dailyTaskStorage(cid, DAILY_STORAGE_REQUIRED)
		local kills = dailyTaskStorage(cid, DAILY_STORAGE_KILLS)
		if kills < 0 then
			kills = 0
		end
		selfSay('Active contract: ' .. kills .. '/' .. required .. ' ' .. name .. '. Keep hunting, then say "reward".')
		return
	end

	if state == DAILY_STATE_OFFER then
		selfSay('You have open contracts waiting. Say "task" to see them again, then 1, 2 or 3.')
		return
	end

	selfSay('No contract yet today. Say "task" to see three options.')
end

function sayStreak(cid)
	dailyTaskEnsureDay(cid)
	local streak = dailyTaskStorage(cid, DAILY_STORAGE_STREAK)
	if streak < 0 then
		streak = 0
	end
	local bonus = dailyTaskStreakBonusPercent(streak)
	if streak <= 0 then
		selfSay('No streak yet. Complete a contract today to start one. Bonus grows up to +50% after 6 days.')
	else
		selfSay('Current streak: ' .. streak .. ' day(s). Next claim bonus: +' .. bonus .. '%. Miss a day and it resets.')
	end
end

function tryAccept(cid, slot)
	dailyTaskEnsureDay(cid)
	local state = dailyTaskStorage(cid, DAILY_STORAGE_STATE)
	if state == DAILY_STATE_CLAIMED then
		selfSay('You already finished today. New contracts tomorrow.')
		return
	end
	if state == DAILY_STATE_ACTIVE or state == DAILY_STATE_DONE then
		selfSay('You already have a contract today. Say "status".')
		return
	end
	if state ~= DAILY_STATE_OFFER then
		selfSay('Ask for "task" first to see today\'s contracts.')
		return
	end

	local offer = dailyTaskAcceptSlot(cid, slot)
	if not offer then
		selfSay('That contract is not available. Say "task" again.')
		return
	end

	selfSay('Accepted: kill ' .. offer.count .. ' ' .. offer.name
		.. '. Reward: ' .. fmtAmount(offer.gold) .. ' gp or ' .. fmtAmount(offer.exp)
		.. ' exp. Good hunting!')
end

function offerRewardChoice(cid)
	dailyTaskEnsureDay(cid)
	local state = dailyTaskStorage(cid, DAILY_STORAGE_STATE)
	if state == DAILY_STATE_CLAIMED then
		selfSay('Already claimed today. See you tomorrow.')
		return
	end
	if state == DAILY_STATE_ACTIVE then
		sayStatus(cid)
		return
	end
	if state ~= DAILY_STATE_DONE then
		selfSay('Finish a contract first. Say "task" or "status".')
		return
	end

	local streak = dailyTaskNextStreak(cid, dailyTaskToday())
	local bonus = dailyTaskStreakBonusPercent(streak)
	local gold = dailyTaskApplyStreak(dailyTaskStorage(cid, DAILY_STORAGE_GOLD), streak)
	local exp = dailyTaskApplyStreak(dailyTaskStorage(cid, DAILY_STORAGE_EXP), streak)

	local bonusText = ''
	if bonus > 0 then
		bonusText = ' (streak +' .. bonus .. '%)'
	end
	selfSay('Choose your reward' .. bonusText .. ': say "gold" for '
		.. fmtAmount(gold) .. ' gp, or "exp" for ' .. fmtAmount(exp) .. ' experience.')
end

function beginClaim(cid, chooseExp)
	dailyTaskEnsureDay(cid)
	local state = dailyTaskStorage(cid, DAILY_STORAGE_STATE)
	if state ~= DAILY_STATE_DONE then
		offerRewardChoice(cid)
		return
	end

	local streak = dailyTaskNextStreak(cid, dailyTaskToday())
	local gold = dailyTaskApplyStreak(dailyTaskStorage(cid, DAILY_STORAGE_GOLD), streak)
	local exp = dailyTaskApplyStreak(dailyTaskStorage(cid, DAILY_STORAGE_EXP), streak)

	pending_reward = { chooseExp = chooseExp }
	talk_state = 1
	if chooseExp then
		selfSay('Claim ' .. fmtAmount(exp) .. ' experience? (yes or si)')
	else
		selfSay('Claim ' .. fmtAmount(gold) .. ' gold? (yes or si)')
	end
end

function onCreatureSay(cid, type, msg)
	msg = string.lower(msg)

	local state = npcHandleMessage(
		cid,
		msg,
		'Hi ' .. creatureGetName(cid) .. '! Daily hunt contracts keep the city safer. Say "task", "status", "reward" or "help".',
		'One moment, ' .. creatureGetName(cid) .. '!'
	)
	if state ~= 'focused' then
		return
	end

	dailyTaskEnsureDay(cid)

	if talk_state == 1 then
		if npcHandlePendingYesNo(cid, msg, function()
			local result, err = dailyTaskClaimRewards(cid, pending_reward and pending_reward.chooseExp)
			pending_reward = nil
			if not result then
				selfSay('I cannot pay that reward right now. Try "reward" again.')
				return
			end
			if result.choseExp then
				selfSay('Done! You gained ' .. fmtAmount(result.exp) .. ' experience. Streak: ' .. result.streak .. '.')
			else
				selfSay('Done! Here are ' .. fmtAmount(result.gold) .. ' gold coins. Streak: ' .. result.streak .. '.')
			end
			selfSay('New contracts tomorrow. Keep the streak going!')
		end, function()
			pending_reward = nil
			selfSay('No problem. Say "gold" or "exp" when you are ready.')
		end) then
			talk_state = 0
		end
		return
	end

	if msgcontains(msg, 'help') or msgcontains(msg, 'ayuda') then
		selfSay(HUNTMASTER_HELP)
	elseif msgcontains(msg, 'streak') or msgcontains(msg, 'racha') then
		sayStreak(cid)
	elseif msgcontains(msg, 'status') or msgcontains(msg, 'report') or msgcontains(msg, 'progress') then
		sayStatus(cid)
	elseif msgcontains(msg, 'reward') or msgcontains(msg, 'claim') or msgcontains(msg, 'premio') then
		offerRewardChoice(cid)
	elseif msg == 'exp' or msg == 'experience' then
		beginClaim(cid, true)
	elseif msg == 'gold' or msg == 'money' or msg == 'oro' then
		beginClaim(cid, false)
	elseif msgcontains(msg, 'task') or msgcontains(msg, 'mission') or msgcontains(msg, 'daily')
		or msgcontains(msg, 'contrato') or msgcontains(msg, 'mision') then
		local st = dailyTaskStorage(cid, DAILY_STORAGE_STATE)
		if st == DAILY_STATE_CLAIMED then
			selfSay('You already claimed today. Come back tomorrow.')
		elseif st == DAILY_STATE_ACTIVE or st == DAILY_STATE_DONE then
			sayStatus(cid)
		else
			sayOffers(cid)
		end
	elseif msg == '1' or msg == 'one' then
		tryAccept(cid, 1)
	elseif msg == '2' or msg == 'two' then
		tryAccept(cid, 2)
	elseif msg == '3' or msg == 'three' then
		tryAccept(cid, 3)
	end
end

function onThink()
	npcOnThink(45, 'Next hunter please...')
end
