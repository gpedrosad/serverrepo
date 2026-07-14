-- Daily hunt contracts for Huntmaster.
-- Monster IDs MUST stay in sync with Player::tryProgressDailyTask catalog in player.cpp.

DAILY_STORAGE_DATE = 9200
DAILY_STORAGE_STATE = 9201
DAILY_STORAGE_MONSTER = 9202
DAILY_STORAGE_REQUIRED = 9203
DAILY_STORAGE_KILLS = 9204
DAILY_STORAGE_STREAK = 9205
DAILY_STORAGE_LAST_CLAIM = 9206
DAILY_STORAGE_OPT1_ID = 9207
DAILY_STORAGE_OPT1_COUNT = 9208
DAILY_STORAGE_OPT2_ID = 9209
DAILY_STORAGE_OPT2_COUNT = 9210
DAILY_STORAGE_OPT3_ID = 9211
DAILY_STORAGE_OPT3_COUNT = 9212
DAILY_STORAGE_GOLD = 9213
DAILY_STORAGE_EXP = 9214
DAILY_STORAGE_BRACKET = 9215

DAILY_STATE_IDLE = 0
DAILY_STATE_OFFER = 1
DAILY_STATE_ACTIVE = 2
DAILY_STATE_DONE = 3
DAILY_STATE_CLAIMED = 4

-- id -> exact monster name (rage prefixes handled in C++)
DAILY_MONSTERS = {
	[1] = 'Rat',
	[2] = 'Spider',
	[3] = 'Troll',
	[4] = 'Rotworm',
	[5] = 'Orc',
	[6] = 'Minotaur',
	[7] = 'Orc Warrior',
	[8] = 'Cyclops',
	[9] = 'Dwarf Guard',
	[10] = 'Larva',
	[11] = 'Dragon',
	[12] = 'Hero',
	[13] = 'Ancient Scarab',
	[14] = 'Behemoth',
	[15] = 'Giant Spider',
	[16] = 'Dragon Lord',
	[17] = 'Hydra',
	[18] = 'Warlock',
	[19] = 'Demon Skeleton',
	[20] = 'Demon',
	[21] = 'Fury'
}

-- Per bracket: pool of monster ids + slot rewards (easy / mid / hard)
DAILY_BRACKETS = {
	{
		key = 'novice',
		label = 'Novice',
		minLevel = 1,
		maxLevel = 20,
		pool = {1, 2, 3, 4, 5},
		counts = {100, 130, 160},
		gold = {800, 1400, 2000},
		exp = {8000, 14000, 20000}
	},
	{
		key = 'adventurer',
		label = 'Adventurer',
		minLevel = 21,
		maxLevel = 40,
		pool = {6, 7, 8, 9, 10},
		counts = {70, 90, 110},
		gold = {3000, 4500, 6000},
		exp = {40000, 65000, 90000}
	},
	{
		key = 'hunter',
		label = 'Hunter',
		minLevel = 41,
		maxLevel = 70,
		pool = {11, 12, 13, 14, 15},
		counts = {55, 70, 90},
		gold = {8000, 11500, 15000},
		exp = {120000, 200000, 280000}
	},
	{
		key = 'elite',
		label = 'Elite',
		minLevel = 71,
		maxLevel = 100,
		pool = {16, 17, 14, 18, 19},
		counts = {45, 60, 75},
		gold = {15000, 22000, 30000},
		exp = {150000, 250000, 350000}
	},
	{
		key = 'legend',
		label = 'Legend',
		minLevel = 101,
		maxLevel = 9999,
		pool = {20, 18, 21, 14, 17},
		counts = {40, 55, 70},
		gold = {25000, 35000, 45000},
		exp = {120000, 200000, 280000}
	}
}

function dailyTaskToday()
	local t = os.date('*t')
	return t.year * 10000 + t.month * 100 + t.day
end

function dailyTaskYesterday(today)
	if today == nil then
		today = dailyTaskToday()
	end
	local y = math.floor(today / 10000)
	local m = math.floor(math.mod(today, 10000) / 100)
	local d = math.mod(today, 100)
	d = d - 1
	if d < 1 then
		m = m - 1
		if m < 1 then
			m = 12
			y = y - 1
		end
		local daysInMonth = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31}
		if math.mod(y, 4) == 0 and (math.mod(y, 100) ~= 0 or math.mod(y, 400) == 0) then
			daysInMonth[2] = 29
		end
		d = daysInMonth[m]
	end
	return y * 10000 + m * 100 + d
end

function dailyTaskStorage(cid, key)
	local v = getPlayerStorageValue(cid, key)
	if v == nil or v == -1 then
		return -1
	end
	return v
end

function dailyTaskSet(cid, key, value)
	setPlayerStorageValue(cid, key, value)
end

function dailyTaskGetBracketIndex(level)
	if level == nil or level < 1 then
		level = 1
	end
	local i
	for i = 1, table.getn(DAILY_BRACKETS) do
		local b = DAILY_BRACKETS[i]
		if level >= b.minLevel and level <= b.maxLevel then
			return i
		end
	end
	return table.getn(DAILY_BRACKETS)
end

function dailyTaskGetBracket(level)
	return DAILY_BRACKETS[dailyTaskGetBracketIndex(level)]
end

function dailyTaskMonsterName(id)
	return DAILY_MONSTERS[id]
end

function dailyTaskNameSeed(name)
	local s = 0
	local i
	if name == nil then
		name = ''
	end
	for i = 1, string.len(name) do
		s = math.mod(s * 33 + string.byte(name, i), 2147483647)
	end
	return s
end

function dailyTaskRngNext(state)
	return math.mod(state * 1103515245 + 12345, 2147483648)
end

function dailyTaskStreakBonusPercent(streak)
	if streak == nil or streak < 2 then
		return 0
	end
	if streak >= 6 then
		return 50
	end
	return (streak - 1) * 10
end

function dailyTaskApplyStreak(amount, streak)
	local bonus = dailyTaskStreakBonusPercent(streak)
	return math.floor(amount * (100 + bonus) / 100)
end

function dailyTaskClearMission(cid, keepStreak)
	local streak = dailyTaskStorage(cid, DAILY_STORAGE_STREAK)
	local lastClaim = dailyTaskStorage(cid, DAILY_STORAGE_LAST_CLAIM)
	dailyTaskSet(cid, DAILY_STORAGE_DATE, dailyTaskToday())
	dailyTaskSet(cid, DAILY_STORAGE_STATE, DAILY_STATE_IDLE)
	dailyTaskSet(cid, DAILY_STORAGE_MONSTER, 0)
	dailyTaskSet(cid, DAILY_STORAGE_REQUIRED, 0)
	dailyTaskSet(cid, DAILY_STORAGE_KILLS, 0)
	dailyTaskSet(cid, DAILY_STORAGE_GOLD, 0)
	dailyTaskSet(cid, DAILY_STORAGE_EXP, 0)
	dailyTaskSet(cid, DAILY_STORAGE_BRACKET, 0)
	dailyTaskSet(cid, DAILY_STORAGE_OPT1_ID, 0)
	dailyTaskSet(cid, DAILY_STORAGE_OPT1_COUNT, 0)
	dailyTaskSet(cid, DAILY_STORAGE_OPT2_ID, 0)
	dailyTaskSet(cid, DAILY_STORAGE_OPT2_COUNT, 0)
	dailyTaskSet(cid, DAILY_STORAGE_OPT3_ID, 0)
	dailyTaskSet(cid, DAILY_STORAGE_OPT3_COUNT, 0)
	if keepStreak then
		if streak < 0 then
			streak = 0
		end
		if lastClaim < 0 then
			lastClaim = 0
		end
		dailyTaskSet(cid, DAILY_STORAGE_STREAK, streak)
		dailyTaskSet(cid, DAILY_STORAGE_LAST_CLAIM, lastClaim)
	else
		dailyTaskSet(cid, DAILY_STORAGE_STREAK, 0)
		dailyTaskSet(cid, DAILY_STORAGE_LAST_CLAIM, 0)
	end
end

-- Lazy day rollover: keeps streak keys, clears active mission if date changed
function dailyTaskEnsureDay(cid)
	local today = dailyTaskToday()
	local stored = dailyTaskStorage(cid, DAILY_STORAGE_DATE)
	if stored ~= today then
		dailyTaskClearMission(cid, true)
		dailyTaskSet(cid, DAILY_STORAGE_DATE, today)
	end
	return today
end

function dailyTaskPickThree(pool, seed)
	local bag = {}
	local i
	for i = 1, table.getn(pool) do
		bag[i] = pool[i]
	end
	local n = table.getn(bag)
	local state = seed
	local picked = {}
	local take = 3
	if take > n then
		take = n
	end
	local t
	for t = 1, take do
		state = dailyTaskRngNext(state)
		local idx = math.mod(state, n - t + 1) + 1
		picked[t] = bag[idx]
		bag[idx] = bag[n - t + 1]
	end
	return picked, state
end

function dailyTaskGenerateOffers(cid, level, playerName)
	local today = dailyTaskEnsureDay(cid)
	local bracketIndex = dailyTaskGetBracketIndex(level)
	local bracket = DAILY_BRACKETS[bracketIndex]
	local seed = today * 31 + bracketIndex * 97 + dailyTaskNameSeed(playerName)
	local ids = dailyTaskPickThree(bracket.pool, seed)

	dailyTaskSet(cid, DAILY_STORAGE_OPT1_ID, ids[1])
	dailyTaskSet(cid, DAILY_STORAGE_OPT1_COUNT, bracket.counts[1])
	dailyTaskSet(cid, DAILY_STORAGE_OPT2_ID, ids[2])
	dailyTaskSet(cid, DAILY_STORAGE_OPT2_COUNT, bracket.counts[2])
	dailyTaskSet(cid, DAILY_STORAGE_OPT3_ID, ids[3])
	dailyTaskSet(cid, DAILY_STORAGE_OPT3_COUNT, bracket.counts[3])
	dailyTaskSet(cid, DAILY_STORAGE_BRACKET, bracketIndex)
	dailyTaskSet(cid, DAILY_STORAGE_STATE, DAILY_STATE_OFFER)
	dailyTaskSet(cid, DAILY_STORAGE_DATE, today)
	dailyTaskSet(cid, DAILY_STORAGE_MONSTER, 0)
	dailyTaskSet(cid, DAILY_STORAGE_REQUIRED, 0)
	dailyTaskSet(cid, DAILY_STORAGE_KILLS, 0)
	dailyTaskSet(cid, DAILY_STORAGE_GOLD, 0)
	dailyTaskSet(cid, DAILY_STORAGE_EXP, 0)
	return bracket, ids
end

function dailyTaskGetOfferSlot(cid, slot)
	local idKey = DAILY_STORAGE_OPT1_ID
	local countKey = DAILY_STORAGE_OPT1_COUNT
	if slot == 2 then
		idKey = DAILY_STORAGE_OPT2_ID
		countKey = DAILY_STORAGE_OPT2_COUNT
	elseif slot == 3 then
		idKey = DAILY_STORAGE_OPT3_ID
		countKey = DAILY_STORAGE_OPT3_COUNT
	end
	local monsterId = dailyTaskStorage(cid, idKey)
	local count = dailyTaskStorage(cid, countKey)
	local bracketIndex = dailyTaskStorage(cid, DAILY_STORAGE_BRACKET)
	if bracketIndex < 1 or bracketIndex > table.getn(DAILY_BRACKETS) then
		return nil
	end
	local bracket = DAILY_BRACKETS[bracketIndex]
	if monsterId < 1 or DAILY_MONSTERS[monsterId] == nil then
		return nil
	end
	return {
		slot = slot,
		monsterId = monsterId,
		name = DAILY_MONSTERS[monsterId],
		count = count,
		gold = bracket.gold[slot],
		exp = bracket.exp[slot],
		bracket = bracket
	}
end

function dailyTaskAcceptSlot(cid, slot)
	local offer = dailyTaskGetOfferSlot(cid, slot)
	if not offer then
		return nil
	end
	dailyTaskSet(cid, DAILY_STORAGE_MONSTER, offer.monsterId)
	dailyTaskSet(cid, DAILY_STORAGE_REQUIRED, offer.count)
	dailyTaskSet(cid, DAILY_STORAGE_KILLS, 0)
	dailyTaskSet(cid, DAILY_STORAGE_GOLD, offer.gold)
	dailyTaskSet(cid, DAILY_STORAGE_EXP, offer.exp)
	dailyTaskSet(cid, DAILY_STORAGE_STATE, DAILY_STATE_ACTIVE)
	return offer
end

function dailyTaskNextStreak(cid, today)
	local lastClaim = dailyTaskStorage(cid, DAILY_STORAGE_LAST_CLAIM)
	local streak = dailyTaskStorage(cid, DAILY_STORAGE_STREAK)
	if streak < 0 then
		streak = 0
	end
	local yesterday = dailyTaskYesterday(today)
	if lastClaim == yesterday then
		return streak + 1
	end
	return 1
end

function dailyTaskClaimRewards(cid, chooseExp)
	local today = dailyTaskEnsureDay(cid)
	local state = dailyTaskStorage(cid, DAILY_STORAGE_STATE)
	if state ~= DAILY_STATE_DONE then
		return nil, 'not_done'
	end

	local gold = dailyTaskStorage(cid, DAILY_STORAGE_GOLD)
	local exp = dailyTaskStorage(cid, DAILY_STORAGE_EXP)
	if gold < 0 then
		gold = 0
	end
	if exp < 0 then
		exp = 0
	end

	local newStreak = dailyTaskNextStreak(cid, today)
	local finalGold = dailyTaskApplyStreak(gold, newStreak)
	local finalExp = dailyTaskApplyStreak(exp, newStreak)

	if chooseExp then
		doPlayerAddExp(cid, finalExp)
	else
		doPlayerAddMoney(cid, finalGold)
	end

	dailyTaskSet(cid, DAILY_STORAGE_STREAK, newStreak)
	dailyTaskSet(cid, DAILY_STORAGE_LAST_CLAIM, today)
	dailyTaskSet(cid, DAILY_STORAGE_STATE, DAILY_STATE_CLAIMED)

	return {
		streak = newStreak,
		bonus = dailyTaskStreakBonusPercent(newStreak),
		gold = finalGold,
		exp = finalExp,
		choseExp = chooseExp
	}, nil
end
