#ifndef __OTSERV_FROST_MINE_H__
#define __OTSERV_FROST_MINE_H__

class Game;
class Player;
class Creature;
class Position;

bool placeFrostMine(Game* game, Player* owner, const Position& pos);
void triggerFrostMine(Game* game, Creature* creature);

#endif
