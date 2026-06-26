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
STATE_DEPOSIT = 1
STATE_WITHDRAW = 2
STATE_TRANSFER_AMOUNT = 3
STATE_TRANSFER_TARGET = 4
STATE_TRANSFER_CONFIRM = 5

pending_transfer_amount = 0
pending_transfer_target = ''

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
	selfSay('I can tell you your balance, deposit money, withdraw money and transfer money to other players. Say balance, deposit, deposit all, withdraw or transfer.')
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
	if amount == nil then
		selfSay('Tell me how much you want to deposit. You can also say deposit all.')
		return
	end

	if amount <= 0 then
		selfSay('You do not have any money to deposit.')
		return
	end

	local result = doPlayerDepositMoney(cid, amount)
	if result == BANK_SUCCESS then
		selfSay('Deposited ' .. amount .. ' gp. Your new balance is ' .. getPlayerBankBalance(cid) .. ' gp.')
		return
	elseif result == BANK_NOT_ENOUGH_MONEY then
		selfSay('You do not have that much money with you.')
		return
	end

	local message = bankerDescribeResult(result)
	if message ~= nil then
		selfSay(message)
	else
		selfSay('I could not complete that deposit.')
	end
end

function bankerDoWithdraw(cid, amount)
	if amount == nil then
		selfSay('Tell me how much you want to withdraw.')
		return
	end

	if amount <= 0 then
		selfSay('You do not have any money to withdraw.')
		return
	end

	local result = doPlayerWithdrawMoney(cid, amount)
	if result == BANK_SUCCESS then
		selfSay('Here you are. You withdrew ' .. amount .. ' gp. Your new balance is ' .. getPlayerBankBalance(cid) .. ' gp.')
		return
	elseif result == BANK_NOT_ENOUGH_BALANCE then
		selfSay('You do not have that much money in your bank account.')
		return
	end

	local message = bankerDescribeResult(result)
	if message ~= nil then
		selfSay(message)
	else
		selfSay('I could not complete that withdrawal.')
	end
end

function bankerAskTransferConfirm()
	selfSay('Do you want to transfer ' .. pending_transfer_amount .. ' gp to ' .. pending_transfer_target .. '?')
	talk_state = STATE_TRANSFER_CONFIRM
end

function bankerConfirmTransfer(cid)
	local result = doPlayerTransferMoneyTo(cid, pending_transfer_amount, pending_transfer_target)
	if result == BANK_SUCCESS then
		selfSay('Transfer complete. Your new balance is ' .. getPlayerBankBalance(cid) .. ' gp.')
	elseif result == BANK_NOT_ENOUGH_BALANCE then
		selfSay('You do not have that much money in your bank account.')
	elseif result == BANK_TARGET_NOT_FOUND then
		selfSay('I could not find that player.')
	elseif result == BANK_SAME_ACCOUNT then
		selfSay('That player belongs to your own account, so the transfer is not needed.')
	else
		local message = bankerDescribeResult(result)
		if message ~= nil then
			selfSay(message)
		else
			selfSay('I could not complete that transfer.')
		end
	end

	bankerReset()
end

function bankerParseCommandAmount(msg, keywordA, keywordB)
	local amountText = string.match(msg, '^' .. keywordA .. '%s+([%w]+)$')
	if amountText == nil and keywordB ~= nil then
		amountText = string.match(msg, '^' .. keywordB .. '%s+([%w]+)$')
	end
	return amountText
end

function bankerParseTransfer(msg)
	local amountText, playerName = string.match(msg, '^transfer%s+([%w]+)%s+to%s+(.+)$')
	if amountText == nil then
		amountText, playerName = string.match(msg, '^transferir%s+([%w]+)%s+a%s+(.+)$')
	end
	return amountText, playerName
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
		'Welcome, ' .. creatureGetName(cid) .. '. I can tell you your balance, deposit money, withdraw money and transfer money to other players.',
		'One moment please, I am helping another customer.',
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

	if msgcontains(msg, 'balance') or msgcontains(msg, 'saldo') then
		bankerGetBalance(cid)
		bankerReset()
		return
	end

	if talk_state == STATE_TRANSFER_CONFIRM then
		if npcHandlePendingYesNo(
			cid,
			msg,
			function() bankerConfirmTransfer(cid) end,
			function()
				selfSay('All right, I cancelled that transfer.')
				bankerReset()
			end
		) then
			return
		end
	end

	if talk_state == STATE_DEPOSIT then
		local amount = bankerResolveAmount(cid, msg, 'money')
		if amount == nil then
			selfSay('Tell me a valid amount to deposit. You can also say deposit all.')
			return
		end

		bankerDoDeposit(cid, amount)
		bankerReset()
		return
	end

	if talk_state == STATE_WITHDRAW then
		local amount = bankerResolveAmount(cid, msg, 'balance')
		if amount == nil then
			selfSay('Tell me a valid amount to withdraw.')
			return
		end

		bankerDoWithdraw(cid, amount)
		bankerReset()
		return
	end

	if talk_state == STATE_TRANSFER_AMOUNT then
		local amount = bankerResolveAmount(cid, msg, 'balance')
		if amount == nil then
			selfSay('Tell me a valid amount to transfer.')
			return
		end

		if amount <= 0 then
			selfSay('You do not have any money to transfer.')
			bankerReset()
			return
		end

		pending_transfer_amount = amount
		selfSay('To which player should I transfer ' .. amount .. ' gp?')
		talk_state = STATE_TRANSFER_TARGET
		return
	end

	if talk_state == STATE_TRANSFER_TARGET then
		local playerName = bankerTrim(msg)
		if playerName == '' then
			selfSay('Tell me the player name for that transfer.')
			return
		end

		pending_transfer_target = playerName
		bankerAskTransferConfirm()
		return
	end

	local depositAmountText = bankerParseCommandAmount(msg, 'deposit', 'depositar')
	if msg == 'deposit' or msg == 'depositar' then
		selfSay('How much would you like to deposit?')
		talk_state = STATE_DEPOSIT
		return
	elseif depositAmountText ~= nil then
		bankerDoDeposit(cid, bankerResolveAmount(cid, depositAmountText, 'money'))
		bankerReset()
		return
	end

	local withdrawAmountText = bankerParseCommandAmount(msg, 'withdraw', 'retirar')
	if withdrawAmountText == nil then
		withdrawAmountText = bankerParseCommandAmount(msg, 'sacar', nil)
	end
	if msg == 'withdraw' or msg == 'retirar' or msg == 'sacar' then
		selfSay('How much would you like to withdraw?')
		talk_state = STATE_WITHDRAW
		return
	elseif withdrawAmountText ~= nil then
		bankerDoWithdraw(cid, bankerResolveAmount(cid, withdrawAmountText, 'balance'))
		bankerReset()
		return
	end

	local transferAmountText, transferPlayerName = bankerParseTransfer(msg)
	if msg == 'transfer' or msg == 'transferir' then
		selfSay('How much would you like to transfer?')
		talk_state = STATE_TRANSFER_AMOUNT
		return
	elseif transferAmountText ~= nil and transferPlayerName ~= nil then
		local amount = bankerResolveAmount(cid, transferAmountText, 'balance')
		if amount == nil then
			selfSay('Tell me a valid amount to transfer.')
			return
		end

		if amount <= 0 then
			selfSay('You do not have any money to transfer.')
			return
		end

		pending_transfer_amount = amount
		pending_transfer_target = bankerTrim(transferPlayerName)
		bankerAskTransferConfirm()
		return
	end

	if msgcontains(msg, 'job') then
		selfSay('I am the banker. I keep your money safe and move it between accounts.')
		return
	end

	bankerShowHelp()
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
