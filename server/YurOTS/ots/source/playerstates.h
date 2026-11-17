//////////////////////////////////////////////////////////////////////
// Estados temporales de jugador que afectan el combate y se consultan
// desde game.cpp. Se mantienen en mapas aparte para no tocar el layout
// de Player/Creature ni el XML de guardado.
//
// Hoy: Postura de contraataque (utito tera).
//////////////////////////////////////////////////////////////////////

#ifndef __OTSERV_PLAYERSTATES_H__
#define __OTSERV_PLAYERSTATES_H__

#include <map>

class Game;
class Player;
class Creature;
#include "magic.h" // attacktype_t

struct CounterStanceState
{
	int hits;            // golpes restantes que absorbe
	int reduction;       // porcentaje de reducción (0-100)
};

extern std::map<unsigned long, CounterStanceState> g_counterStance;

// Si el jugador tiene postura activa, reduce el daño y, contra monstruos,
// devuelve un contraataque. Devuelve el daño ya reducido.
int applyCounterStance(Game* game, Player* defender, Creature* attacker,
	int damage, attacktype_t atype);

#endif
