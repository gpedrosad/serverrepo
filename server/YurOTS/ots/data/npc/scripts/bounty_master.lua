focus = 0
talk_start = 0
talk_state = 0
target = 0
following = false
attacking = false

BOUNTY_SUCCESS = 1
BOUNTY_INVALID_AMOUNT = -21
BOUNTY_SPONSOR_NOT_FOUND = -22
BOUNTY_ACCOUNT_NOT_FOUND = -23
BOUNTY_NOT_ENOUGH_BALANCE = -24
BOUNTY_TARGET_NOT_FOUND = -25
BOUNTY_SAME_ACCOUNT = -26
BOUNTY_SAVE_FAILED = -27
BOUNTY_INVALID_TARGET = -28
BOUNTY_TOO_LARGE = -29

STATE_NONE = 0
STATE_BOUNTY_CONFIRM = 1

pending_bounty_amount = 0
pending_bounty_target = ''

function bountyTrim(text)
	if text == nil then
		return ''
	end
	text = string.gsub(text, '^%s+', '')
	text = string.gsub(text, '%s+$', '')
	return text
end

function bountyReset()
	talk_state = STATE_NONE
	pending_bounty_amount = 0
	pending_bounty_target = ''
end

function bountyResolveAmount(cid, text)
	text = bountyTrim(text)
	if text == '' then
		return nil
	end

	if text == 'all' or text == 'todo' then
		return getPlayerBankBalance(cid)
	end

	local amount = tonumber(text)
	if amount == nil then
		return nil
	end

	amount = math.floor(amount)
	if amount <= 0 then
		return nil
	end

	return amount
end

function bountyShowHelp()
	selfSay('Use your bank balance to place a contract. Say bounty 10000 name.')
	selfSay('Examples: bounty 50000 Yurez | hunt all Cachero | status Yurez')
end

function bountyDescribeResult(result)
	if result == BOUNTY_ACCOUNT_NOT_FOUND then
		return 'I could not open your bank account right now.'
	elseif result == BOUNTY_SAVE_FAILED then
		return 'The ledger is busy right now. Try again in a moment.'
	elseif result == BOUNTY_SPONSOR_NOT_FOUND then
		return 'I cannot help you right now.'
	elseif result == BOUNTY_INVALID_AMOUNT then
		return 'Tell me a valid amount of gold.'
	elseif result == BOUNTY_NOT_ENOUGH_BALANCE then
		return 'You do not have that much in the bank.'
	elseif result == BOUNTY_TARGET_NOT_FOUND then
		return 'I could not find that player.'
	elseif result == BOUNTY_SAME_ACCOUNT then
		return 'You cannot place a bounty on your own account.'
	elseif result == BOUNTY_INVALID_TARGET then
		return 'That target cannot be hunted.'
	elseif result == BOUNTY_TOO_LARGE then
		return 'That bounty is too large for my ledger.'
	end
	return nil
end

function bountyShowStatus(targetName)
	local resolved = bountyTrim(targetName)
	if resolved == '' then
		selfSay('Say status name.')
		return false
	end

	local bounty = getPlayerBountyByName(resolved)
	if bounty < 0 then
		selfSay('I could not find that player.')
	elseif bounty == 0 then
		selfSay(resolved .. ' has no active bounty.')
	else
		selfSay(resolved .. ' is worth ' .. bounty .. ' gp.')
	end
	return true
end

function bountyAskConfirm()
	selfSay('Place a bounty of ' .. pending_bounty_amount .. ' gp on ' .. pending_bounty_target .. ' using your bank balance? yes or no.')
	talk_state = STATE_BOUNTY_CONFIRM
end

function bountyPrepare(cid, amountText, targetName)
	local amount = bountyResolveAmount(cid, amountText)
	if amount == nil then
		selfSay('Say bounty 10000 name or hunt all name.')
		return false
	end
	if amount <= 0 then
		selfSay('You do not have any gold in the bank for that contract.')
		return false
	end

	targetName = bountyTrim(targetName)
	if targetName == '' then
		selfSay('Say bounty 10000 name.')
		return false
	end

	pending_bounty_amount = amount
	pending_bounty_target = targetName
	bountyAskConfirm()
	return true
end

function bountyConfirm(cid)
	local amount = pending_bounty_amount
	local targetName = pending_bounty_target
	bountyReset()

	local result, total, resolved = doPlayerPlaceBounty(cid, amount, targetName)
	if result == BOUNTY_SUCCESS then
		if resolved == nil or resolved == '' then
			resolved = targetName
		end
		selfSay('Contract posted on ' .. resolved .. '. Current bounty: ' .. total .. ' gp.')
	else
		local message = bountyDescribeResult(result)
		selfSay(message or 'I could not post that contract.')
	end
end

function bountyHandleConfirm(cid, msg)
	if talk_state ~= STATE_BOUNTY_CONFIRM then
		return false
	end

	return npcHandlePendingYesNo(
		cid, msg,
		function() bountyConfirm(cid) end,
		function()
			selfSay('Contract cancelled.')
			bountyReset()
		end
	)
end

function bountyParsePlace(msg)
	local amountText, playerName

	amountText, playerName = string.match(msg, '^bounty%s+([%w]+)%s+(.+)$')
	if amountText == nil then
		amountText, playerName = string.match(msg, '^hunt%s+([%w]+)%s+(.+)$')
	end
	if amountText == nil then
		amountText, playerName = string.match(msg, '^recompensa%s+([%w]+)%s+(.+)$')
	end
	if amountText == nil then
		amountText, playerName = string.match(msg, '^cazar%s+([%w]+)%s+(.+)$')
	end

	return amountText, playerName
end

function bountyParseStatus(msg)
	local playerName = string.match(msg, '^status%s+(.+)$')
	if playerName == nil then
		playerName = string.match(msg, '^wanted%s+(.+)$')
	end
	if playerName == nil then
		playerName = string.match(msg, '^precio%s+(.+)$')
	end
	if playerName == nil then
		playerName = string.match(msg, '^recompensa%s+de%s+(.+)$')
	end
	return playerName
end

function bountyTryCommand(cid, msg)
	if msgcontains(msg, 'most wanted') then
		selfSay('Check the website for the full Most Wanted list.')
		return true
	end

	local statusTarget = bountyParseStatus(msg)
	if statusTarget ~= nil then
		bountyShowStatus(statusTarget)
		return true
	end

	local amountText, playerName = bountyParsePlace(msg)
	if amountText ~= nil and playerName ~= nil then
		bountyPrepare(cid, amountText, playerName)
		return true
	end

	return false
end

function onThingMove(creature, thing, oldpos, oldstackpos)
end

function onCreatureAppear(creature)
end

function onCreatureDisappear(cid, pos)
	if focus == cid then
		bountyReset()
	end
	npcOnCreatureDisappear(cid)
end

function onCreatureTurn(creature)
end

function onCreatureSay(cid, type, msg)
	msg = string.lower(msg)

	local state = npcHandleMessage(
		cid,
		msg,
		'Welcome, ' .. creatureGetName(cid) .. '. I post contracts from your bank balance. Say help for examples.',
		'One moment please.',
		'Safe hunting!'
	)
	if state == 'greet' then
		bountyReset()
		return
	elseif state ~= 'focused' then
		return
	end

	if npcIsHelp(msg) or msg == 'bounty' or msg == 'hunt' or msg == 'wanted' or msg == 'most wanted' then
		bountyShowHelp()
		return
	end

	if talk_state ~= STATE_NONE then
		if bountyHandleConfirm(cid, msg) then
			return
		end
		if bountyTryCommand(cid, msg) then
			return
		end
		selfSay('Please say yes or no.')
		return
	end

	if bountyTryCommand(cid, msg) then
		return
	end

	if msgcontains(msg, 'job') then
		selfSay('I keep the contracts and the Most Wanted ledger.')
		return
	end

	bountyShowHelp()
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
