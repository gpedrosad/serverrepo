//////////////////////////////////////////////////////////////////////
// Cooldowns propios por hechizo. Ver spellcooldown.h.
//////////////////////////////////////////////////////////////////////

#include "definitions.h"
#include "otsystem.h"
#include "spellcooldown.h"

#include <map>
#include <string>

namespace
{
	// (player id, cooldown name) -> OTSYS_TIME() hasta el que está en cooldown.
	std::map<std::pair<unsigned long, std::string>, __int64> cooldownUntil;

	void prune(__int64 now)
	{
		if(cooldownUntil.size() < 512)
			return;
		std::map<std::pair<unsigned long, std::string>, __int64>::iterator it = cooldownUntil.begin();
		while(it != cooldownUntil.end()) {
			if(it->second <= now)
				cooldownUntil.erase(it++);
			else
				++it;
		}
	}
}

bool PlayerSpellCooldown::isOnCooldown(unsigned long playerId, const std::string& name)
{
	return remaining(playerId, name) > 0;
}

int PlayerSpellCooldown::remaining(unsigned long playerId, const std::string& name)
{
	std::map<std::pair<unsigned long, std::string>, __int64>::iterator it =
		cooldownUntil.find(std::make_pair(playerId, name));
	if(it == cooldownUntil.end())
		return 0;
	__int64 left = it->second - OTSYS_TIME();
	if(left <= 0) {
		cooldownUntil.erase(it);
		return 0;
	}
	return (int)left;
}

void PlayerSpellCooldown::set(unsigned long playerId, const std::string& name, int ms)
{
	__int64 now = OTSYS_TIME();
	prune(now);
	if(ms <= 0) {
		cooldownUntil.erase(std::make_pair(playerId, name));
		return;
	}
	cooldownUntil[std::make_pair(playerId, name)] = now + ms;
}
