//////////////////////////////////////////////////////////////////////
// Exhausted mágico de jugadores con hora exacta. Ver exhaust.h.
//////////////////////////////////////////////////////////////////////

#include "definitions.h"
#include "otsystem.h"
#include "player.h"
#include "exhaust.h"

#include <map>

namespace
{
	// id del jugador -> OTSYS_TIME() hasta el que está exhausted.
	// Se usa siempre con gameLock tomado (game.cpp / spells.cpp).
	std::map<unsigned long, __int64> exhaustedUntil;

	void prune(__int64 now)
	{
		if(exhaustedUntil.size() < 256)
			return;
		std::map<unsigned long, __int64>::iterator it = exhaustedUntil.begin();
		while(it != exhaustedUntil.end()) {
			if(it->second <= now)
				exhaustedUntil.erase(it++);
			else
				++it;
		}
	}
}

bool PlayerExhaust::isExhausted(const Player* player)
{
	return remaining(player) > 0;
}

int PlayerExhaust::remaining(const Player* player)
{
	if(!player)
		return 0;
	std::map<unsigned long, __int64>::iterator it = exhaustedUntil.find(player->getID());
	if(it == exhaustedUntil.end())
		return 0;
	__int64 left = it->second - OTSYS_TIME();
	if(left <= 0) {
		exhaustedUntil.erase(it);
		return 0;
	}
	return (int)left;
}

void PlayerExhaust::set(const Player* player, int ms)
{
	if(!player)
		return;
	__int64 now = OTSYS_TIME();
	prune(now);
	if(ms <= 0) {
		exhaustedUntil.erase(player->getID());
		return;
	}
	exhaustedUntil[player->getID()] = now + ms;
}

void PlayerExhaust::add(const Player* player, int ms)
{
	if(!player || ms <= 0)
		return;
	set(player, remaining(player) + ms);
}

void PlayerExhaust::cap(const Player* player, int ms)
{
	if(!player)
		return;
	if(remaining(player) > ms)
		set(player, ms);
}
