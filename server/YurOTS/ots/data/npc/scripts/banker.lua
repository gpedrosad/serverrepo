focus = 0
talk_start = 0
talk_state = 0
target = 0
following = false
attacking = false

BANK_SUCCESS = 1
BANK_INVALID_AMOUNT = -1
BANK_PLAYER_NOT_FOUND = -2
BANK_ACCOUNT_NOT_FOUND = -3
BANK_NOT_ENOUGH_MONEY = -4
BANK_NOT_ENOUGH_BALANCE = -5
BANK_TARGET_NOT_FOUND = -6
BANK_SAME_ACCOUNT = -7
BANK_SAVE_FAILED = -8

STATE_NONE = 0
STATE_DEPOSIT_CONFIRM = 1
STATE_WITHDRAW_CONFIRM = 2
STATE_TRANSFER_CONFIRM = 3

pending_transfer_amount = 0
pending_transfer_target = ''
pending_deposit_amount = 0
pending_withdraw_amount = 0

function bankerTrim(text)
	if text == nil then
		return ''
	end
	text = string.gsub(text, '^%s+', '')
	text = string.gsub(text, '%s+$', '')
	return text
end

function bankerReset()
	talk_state = STATE_NONE
	pending_transfer_amount = 0
	pending_transfer_target = ''
	pending_deposit_amount = 0
	pending_withdraw_amount = 0
end

function bankerGetBalance(cid)
	local balance = getPlayerBankBalance(cid)
	if balance < 0 then
		selfSay('I could not read your bank balance right now.')
	else
		selfSay('Your bank balance is ' .. balance .. ' gp.')
	end
end

function bankerResolveAmount(cid, text, source)
	text = bankerTrim(text)
	if text == '' then
		return nil
	end

	if text == 'all' or text == 'todo' then
		if source == 'money' then
			return getPlayerMoney(cid)
		end
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

function bankerShowHelp()
	selfSay('Examples: balance | deposit 10000 | withdraw 5000 | transfer 10000 name | deposit all')
	selfSay('I ask yes or no before moving gold.')
end

function bankerDescribeResult(result)
	if result == BANK_ACCOUNT_NOT_FOUND then
		return 'Your account could not be loaded right now.'
	elseif result == BANK_SAVE_FAILED then
		return 'The bank vault is busy right now. Try again in a moment.'
	elseif result == BANK_PLAYER_NOT_FOUND then
		return 'I cannot help you right now.'
	elseif result == BANK_INVALID_AMOUNT then
		return 'Tell me a valid amount of gold.'
	end
	return nil
end

function bankerDoDeposit(cid, amount)
	local result = doPlayerDepositMoney(cid, amount)
	if result == BANK_SUCCESS then
		selfSay('Deposited ' .. amount .. ' gp. Balance: ' .. getPlayerBankBalance(cid) .. ' gp.')
	elseif result == BANK_NOT_ENOUGH_MONEY then
		selfSay('You do not have that much money with you.')
	else
		local message = bankerDescribeResult(result)
		selfSay(message or 'I could not complete that deposit.')
	end
end

function bankerDoWithdraw(cid, amount)
	local result = doPlayerWithdrawMoney(cid, amount)
	if result == BANK_SUCCESS then
		selfSay('Withdrew ' .. amount .. ' gp. Balance: ' .. getPlayerBankBalance(cid) .. ' gp.')
	elseif result == BANK_NOT_ENOUGH_BALANCE then
		selfSay('You do not have that much in the bank.')
	else
		local message = bankerDescribeResult(result)
		selfSay(message or 'I could not complete that withdrawal.')
	end
end

function bankerAskDepositConfirm()
	selfSay('Deposit ' .. pending_deposit_amount .. ' gp? yes or no.')
	talk_state = STATE_DEPOSIT_CONFIRM
end

function bankerAskWithdrawConfirm()
	selfSay('Withdraw ' .. pending_withdraw_amount .. ' gp? yes or no.')
	talk_state = STATE_WITHDRAW_CONFIRM
end

function bankerAskTransferConfirm()
	selfSay('Transfer ' .. pending_transfer_amount .. ' gp to ' .. pending_transfer_target .. '? yes or no.')
	talk_state = STATE_TRANSFER_CONFIRM
end

function bankerPrepareDeposit(cid, amount)
	if amount == nil then
		selfSay('Say deposit 10000 or deposit all.')
		return false
	end
	if amount <= 0 then
		selfSay('You do not have any money to deposit.')
		return false
	end
	pending_deposit_amount = amount
	bankerAskDepositConfirm()
	return true
end

function bankerPrepareWithdraw(cid, amount)
	if amount == nil then
		selfSay('Say withdraw 10000 or withdraw all.')
		return false
	end
	if amount <= 0 then
		selfSay('You do not have any money to withdraw.')
		return false
	end
	pending_withdraw_amount = amount
	bankerAskWithdrawConfirm()
	return true
end

function bankerPrepareTransfer(cid, amountText, playerName)
	local amount = bankerResolveAmount(cid, amountText, 'balance')
	if amount == nil then
		selfSay('Say transfer 10000 name')
		return false
	end
	if amount <= 0 then
		selfSay('You do not have any money to transfer.')
		return false
	end
	playerName = bankerTrim(playerName)
	if playerName == '' then
		selfSay('Say transfer 10000 name')
		return false
	end
	pending_transfer_amount = amount
	pending_transfer_target = playerName
	bankerAskTransferConfirm()
	return true
end

function bankerConfirmDeposit(cid)
	local amount = pending_deposit_amount
	bankerReset()
	bankerDoDeposit(cid, amount)
end

function bankerConfirmWithdraw(cid)
	local amount = pending_withdraw_amount
	bankerReset()
	bankerDoWithdraw(cid, amount)
end

function bankerConfirmTransfer(cid)
	local amount = pending_transfer_amount
	local target = pending_transfer_target
	bankerReset()
	local result = doPlayerTransferMoneyTo(cid, amount, target)
	if result == BANK_SUCCESS then
		selfSay('Transfer complete. Balance: ' .. getPlayerBankBalance(cid) .. ' gp.')
	elseif result == BANK_NOT_ENOUGH_BALANCE then
		selfSay('You do not have that much in the bank.')
	elseif result == BANK_TARGET_NOT_FOUND then
		selfSay('I could not find that player.')
	elseif result == BANK_SAME_ACCOUNT then
		selfSay('That player is on your account.')
	else
		local message = bankerDescribeResult(result)
		selfSay(message or 'I could not complete that transfer.')
	end
end

function bankerParseAmountAfter(msg, keywordA, keywordB)
	local amountText = string.match(msg, '^' .. keywordA .. '%s+([%w]+)')
	if amountText == nil and keywordB ~= nil then
		amountText = string.match(msg, '^' .. keywordB .. '%s+([%w]+)')
	end
	return amountText
end

function bankerParseTransfer(msg)
	local amountText, playerName

	amountText, playerName = string.match(msg, '^transfer%s+([%w]+)%s+to%s+(.+)$')
	if amountText == nil then
		amountText, playerName = string.match(msg, '^transfer%s+([%w]+)%s+(.+)$')
	end
	if amountText == nil then
		amountText, playerName = string.match(msg, '^transferir%s+([%w]+)%s+a%s+(.+)$')
	end
	if amountText == nil then
		amountText, playerName = string.match(msg, '^transferir%s+([%w]+)%s+(.+)$')
	end

	return amountText, playerName
end

function bankerHandleConfirm(cid, msg)
	if talk_state == STATE_DEPOSIT_CONFIRM then
		return npcHandlePendingYesNo(
			cid, msg,
			function() bankerConfirmDeposit(cid) end,
			function()
				selfSay('Deposit cancelled.')
				bankerReset()
			end
		)
	end

	if talk_state == STATE_WITHDRAW_CONFIRM then
		return npcHandlePendingYesNo(
			cid, msg,
			function() bankerConfirmWithdraw(cid) end,
			function()
				selfSay('Withdrawal cancelled.')
				bankerReset()
			end
		)
	end

	if talk_state == STATE_TRANSFER_CONFIRM then
		return npcHandlePendingYesNo(
			cid, msg,
			function() bankerConfirmTransfer(cid) end,
			function()
				selfSay('Transfer cancelled.')
				bankerReset()
			end
		)
	end

	return false
end

function bankerTryCommand(cid, msg)
	if msgcontains(msg, 'balance') or msgcontains(msg, 'saldo') then
		bankerGetBalance(cid)
		return true
	end

	local depositAmount = bankerParseAmountAfter(msg, 'deposit', 'depositar')
	if depositAmount ~= nil then
		bankerPrepareDeposit(cid, bankerResolveAmount(cid, depositAmount, 'money'))
		return true
	end

	local withdrawAmount = bankerParseAmountAfter(msg, 'withdraw', 'retirar')
	if withdrawAmount == nil then
		withdrawAmount = bankerParseAmountAfter(msg, 'sacar', nil)
	end
	if withdrawAmount ~= nil then
		bankerPrepareWithdraw(cid, bankerResolveAmount(cid, withdrawAmount, 'balance'))
		return true
	end

	local transferAmount, transferTarget = bankerParseTransfer(msg)
	if transferAmount ~= nil and transferTarget ~= nil then
		bankerPrepareTransfer(cid, transferAmount, transferTarget)
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
		bankerReset()
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
		'Welcome, ' .. creatureGetName(cid) .. '. Say balance, deposit, withdraw or transfer. Say help for examples.',
		'One moment please.',
		'Safe travels!'
	)
	if state == 'greet' then
		bankerReset()
		return
	elseif state ~= 'focused' then
		return
	end

	if npcIsHelp(msg) or msgcontains(msg, 'bank') or msgcontains(msg, 'banco') then
		bankerShowHelp()
		return
	end

	if talk_state ~= STATE_NONE then
		if bankerHandleConfirm(cid, msg) then
			return
		end
		if bankerTryCommand(cid, msg) then
			return
		end
		selfSay('Please say yes or no.')
		return
	end

	if bankerTryCommand(cid, msg) then
		return
	end

	if msgcontains(msg, 'job') then
		selfSay('I am the banker.')
		return
	end

	bankerShowHelp()
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
