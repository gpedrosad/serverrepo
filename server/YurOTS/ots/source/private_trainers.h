//////////////////////////////////////////////////////////////////////
// Private house trainer dummy persistence
//////////////////////////////////////////////////////////////////////

#ifndef __PRIVATE_TRAINERS_H__
#define __PRIVATE_TRAINERS_H__

#include "const76.h"
#include "position.h"

#include <string>

class Game;
class Monster;
class Player;

class PrivateTrainers
{
public:
	static bool Load(Game* game);
	static bool Save();
	static bool Place(Game* game, Player* player, const Position& pos, std::string& message);

	static const unsigned short ITEM_ID = ITEM_PRIVATE_TRAINER_DUMMY;
	static const char* MONSTER_NAME;

private:
	static Monster* Spawn(Game* game, const Position& pos, std::string& message);
};

#endif // __PRIVATE_TRAINERS_H__
