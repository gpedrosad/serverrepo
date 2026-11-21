//////////////////////////////////////////////////////////////////////
// Padrinazgo (docs/gameplay/PADRINAZGO.md): un jugador nuevo elige padrino con !padrino y, cuando llega a
// ciertos niveles, los dos reciben premio. Se guarda en data/sponsors.xml (runtime, no va a git).
//////////////////////////////////////////////////////////////////////

#ifndef __SPONSOR_H__
#define __SPONSOR_H__

#include <string>

class Game;
class Player;

// Caja de regalo del rango de un nivel (player.cpp, LEVEL_UP_REWARDS.md).
unsigned short levelGiftItemId(int lv);

namespace Sponsors
{
	bool Load();
	// !padrino, !padrino Nombre, !padrino aceptar Nombre
	void command(Game* game, Player* player, const std::string& param);
	// después de subir de nivel: hitos del ahijado
	void onLevel(Player* player);
	// al entrar: premios pendientes del padrino y aviso a los nuevos
	void onLogin(Player* player);
}

#endif
