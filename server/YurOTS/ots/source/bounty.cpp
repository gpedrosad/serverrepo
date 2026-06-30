#include "bounty.h"

#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>

#include "game.h"
#include "ioaccount.h"
#include "ioplayer.h"
#include "player.h"

namespace
{
	bool persistPlayerState(Player* player)
	{
		return player && IOPlayer::instance()->savePlayer(player);
	}

	bool loadTargetRecord(const std::string& targetName, Player& player)
	{
		return IOPlayer::instance()->loadPlayer(&player, targetName);
	}

	bool loadAccountByNumber(unsigned long accountNumber, Account& account)
	{
		account = IOAccount::instance()->loadAccount(accountNumber);
		return account.accnumber == accountNumber;
	}

	bool canAccumulateBounty(uint64_t currentValue, uint64_t addValue)
	{
		return currentValue <= (std::numeric_limits<uint64_t>::max() - addValue);
	}

	void notifyBountyPlaced(const std::string& sponsorName, const std::string& targetName,
		uint64_t placedAmount, uint64_t totalAmount)
	{
		std::ostringstream msg;
		msg << sponsorName << " placed a bounty of " << placedAmount << " gp on "
			<< targetName << ". Reward for killing " << targetName
			<< " is now " << totalAmount << " gp.";
		const std::string text = msg.str();

		std::cout << "\033[1;31m" << text << "\033[0m" << std::endl;
		std::cout.flush();

		std::ofstream serverLog("server.log", std::ios::app);
		if(serverLog.is_open()) {
			serverLog << text << std::endl;
		}

		for(AutoList<Player>::listiterator it = Player::listPlayer.list.begin();
			it != Player::listPlayer.list.end(); ++it) {
			if(it->second)
				it->second->sendTextMessage(MSG_RED_TEXT, text.c_str());
		}
	}
}

int BountySystem::placeBounty(Game* game, Player* sponsor, uint64_t amount, const std::string& targetName,
	uint64_t* targetTotal, std::string* resolvedTargetName)
{
	if(amount == 0)
		return BOUNTY_ACTION_INVALID_AMOUNT;

	if(!sponsor)
		return BOUNTY_ACTION_SPONSOR_NOT_FOUND;

	Account sponsorAccount;
	if(!loadAccountByNumber((unsigned long)sponsor->getAccount(), sponsorAccount))
		return BOUNTY_ACTION_ACCOUNT_NOT_FOUND;

	if(sponsorAccount.balance < amount)
		return BOUNTY_ACTION_NOT_ENOUGH_BALANCE;

	Player targetRecord(targetName, NULL);
	if(!loadTargetRecord(targetName, targetRecord))
		return BOUNTY_ACTION_TARGET_NOT_FOUND;

	if(!targetRecord.isAttackable())
		return BOUNTY_ACTION_INVALID_TARGET;

	if(targetRecord.getAccount() == sponsor->getAccount())
		return BOUNTY_ACTION_SAME_ACCOUNT;

	Player* liveTarget = game ? game->getPlayerByName(targetRecord.getName()) : NULL;
	Player* target = liveTarget ? liveTarget : &targetRecord;

	if(!target->isAttackable())
		return BOUNTY_ACTION_INVALID_TARGET;

	const uint64_t oldTargetBounty = target->getBountyValue();
	if(!canAccumulateBounty(oldTargetBounty, amount))
		return BOUNTY_ACTION_TOO_LARGE;

	target->setBountyValue(oldTargetBounty + amount);
	sponsorAccount.balance -= amount;

	if(!IOAccount::instance()->saveAccount(sponsorAccount)) {
		target->setBountyValue(oldTargetBounty);
		return BOUNTY_ACTION_SAVE_FAILED;
	}

	if(!persistPlayerState(target)) {
		target->setBountyValue(oldTargetBounty);
		sponsorAccount.balance += amount;
		IOAccount::instance()->saveAccount(sponsorAccount);
		return BOUNTY_ACTION_SAVE_FAILED;
	}

	if(targetTotal)
		*targetTotal = target->getBountyValue();

	if(resolvedTargetName)
		*resolvedTargetName = target->getName();

	notifyBountyPlaced(sponsor->getName(), target->getName(), amount, target->getBountyValue());

	return BOUNTY_ACTION_SUCCESS;
}

int64_t BountySystem::getBountyByName(Game* game, const std::string& targetName, std::string* resolvedTargetName)
{
	Player targetRecord(targetName, NULL);
	if(!loadTargetRecord(targetName, targetRecord))
		return -1;

	Player* liveTarget = game ? game->getPlayerByName(targetRecord.getName()) : NULL;
	Player* target = liveTarget ? liveTarget : &targetRecord;

	if(resolvedTargetName)
		*resolvedTargetName = target->getName();

	return (int64_t)target->getBountyValue();
}

bool BountySystem::transferBountyOnKill(Player* victim, Player* killer, uint64_t* transferred, uint64_t* killerTotal)
{
	if(!victim || !killer || victim == killer)
		return false;

	if(!killer->isAttackable())
		return false;

	const uint64_t bounty = victim->getBountyValue();
	if(bounty == 0)
		return false;

	const uint64_t killerBounty = killer->getBountyValue();
	if(!canAccumulateBounty(killerBounty, bounty))
		return false;

	victim->setBountyValue(0);
	killer->setBountyValue(killerBounty + bounty);

	if(!persistPlayerState(killer)) {
		victim->setBountyValue(bounty);
		killer->setBountyValue(killerBounty);
		return false;
	}

	if(!persistPlayerState(victim)) {
		victim->setBountyValue(bounty);
		killer->setBountyValue(killerBounty);
		if(!persistPlayerState(killer)) {
			std::cout << "Failed to roll back killer bounty transfer for " << killer->getName() << std::endl;
		}
		return false;
	}

	if(transferred)
		*transferred = bounty;

	if(killerTotal)
		*killerTotal = killer->getBountyValue();

	return true;
}
