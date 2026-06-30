#ifndef __BOUNTY_H__
#define __BOUNTY_H__

#include <stdint.h>
#include <string>

class Game;
class Player;

enum BountyActionResult {
	BOUNTY_ACTION_SUCCESS = 1,
	BOUNTY_ACTION_INVALID_AMOUNT = -21,
	BOUNTY_ACTION_SPONSOR_NOT_FOUND = -22,
	BOUNTY_ACTION_ACCOUNT_NOT_FOUND = -23,
	BOUNTY_ACTION_NOT_ENOUGH_BALANCE = -24,
	BOUNTY_ACTION_TARGET_NOT_FOUND = -25,
	BOUNTY_ACTION_SAME_ACCOUNT = -26,
	BOUNTY_ACTION_SAVE_FAILED = -27,
	BOUNTY_ACTION_INVALID_TARGET = -28,
	BOUNTY_ACTION_TOO_LARGE = -29
};

namespace BountySystem
{
	int placeBounty(Game* game, Player* sponsor, uint64_t amount, const std::string& targetName,
		uint64_t* targetTotal = NULL, std::string* resolvedTargetName = NULL);

	int64_t getBountyByName(Game* game, const std::string& targetName,
		std::string* resolvedTargetName = NULL);

	bool transferBountyOnKill(Player* victim, Player* killer,
		uint64_t* transferred = NULL, uint64_t* killerTotal = NULL);
}

#endif
