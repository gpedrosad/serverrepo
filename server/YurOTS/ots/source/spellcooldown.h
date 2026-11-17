//////////////////////////////////////////////////////////////////////
// Cooldowns propios por hechizo (por jugador), independientes del
// exhausted mágico global. Se usan para spells con recarga larga que no
// deberían spamearse aunque el exhausted normal ya haya pasado.
//
// Clave: (id del jugador, nombre del cooldown). El nombre es arbitrario;
// cada spell elige el suyo (por convención, sus words).
//
// Se guarda en un mapa aparte (no como miembro de Player) para no alterar
// el layout de la clase ni el XML de guardado. No persiste entre logouts.
// Doc: docs/gameplay/SPELLS_NOV2026.md (nuevos spells con cooldown propio).
//////////////////////////////////////////////////////////////////////

#ifndef __OTSERV_SPELLCOOLDOWN_H__
#define __OTSERV_SPELLCOOLDOWN_H__

#include <string>

namespace PlayerSpellCooldown
{
	// true si el cooldown aún no terminó.
	bool isOnCooldown(unsigned long playerId, const std::string& name);
	// ms que le quedan (0 si no está en cooldown).
	int remaining(unsigned long playerId, const std::string& name);
	// Activa el cooldown por `ms` desde ahora.
	void set(unsigned long playerId, const std::string& name, int ms);
}

#endif
