//////////////////////////////////////////////////////////////////////
// Exhausted mágico de jugadores con hora exacta (ms).
//
// Antes: Creature::exhaustedTicks se descontaba de a 1000 en el think del jugador
// (cada 1 s), así que 2000 ms duraba entre 1 y 2 s y 1000 ms entre 0 y 1 s según
// el momento del cast. Ahora se guarda "exhausted hasta" y se compara con el reloj.
//
// Se guarda en un mapa por id de jugador (no como miembro de Player/Creature) para
// no cambiar el layout de las clases: ver docs/gameplay/NPC_CONFIRMATION.md
// (heap corruption bajo QEMU i386 al agregar miembros).
// Doc: docs/gameplay/SPELL_EXHAUSTION.md
//////////////////////////////////////////////////////////////////////

#ifndef __OTSERV_EXHAUST_H__
#define __OTSERV_EXHAUST_H__

class Player;

namespace PlayerExhaust
{
	// true si el jugador sigue exhausted (no mira access; lo chequea quien llama).
	bool isExhausted(const Player* player);
	// Exhausted por `ms` desde ahora (reemplaza lo que hubiera).
	void set(const Player* player, int ms);
	// Suma `ms` al exhausted actual (yell con exhaustedadd).
	void add(const Player* player, int ms);
	// Si le quedan más de `ms`, lo baja a `ms` (reduceExhaustion*).
	void cap(const Player* player, int ms);
	// ms que le quedan (0 si no está exhausted).
	int remaining(const Player* player);
}

#endif
