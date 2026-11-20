#ifndef YUROTS_MELEE_RELICS_H
#define YUROTS_MELEE_RELICS_H

#include <algorithm>
#include <stdint.h>
#include "const76.h"

inline bool isMeleeRelic(unsigned short id)
{
	return id == ITEM_RIFTBLADE || id == ITEM_AETHERCLEAVER || id == ITEM_GRAVITON_MAUL;
}

enum MeleeRelicBalance {
	RIFTBLADE_DELAY_MS = 1200,
	AETHERCLEAVER_DELAY_MS = 1333,
	GRAVITON_DELAY_MS = 1600,
	RIFT_COMBO_TIMEOUT_MS = 6000,
	RIFT_MIN_DAMAGE = 22,
	RIFT_MAX_DAMAGE = 34,
	AETHER_MANA_PERCENT = 12,
	AETHER_MANA_CAP = 10,
	GRAVITON_CHANCE = 25,
	GRAVITON_BASE_DAMAGE = 12,
	GRAVITON_ARMOR_CAP = 60
};

// Per-player, transient: target changes, misses, unequipping and idle time reset it.
struct RiftCombo {
	unsigned long target;
	int hits;
	int64_t lastHit;
	RiftCombo() : target(0), hits(0), lastHit(0) {}
	void reset() { target = 0; hits = 0; lastHit = 0; }
	bool advance(unsigned long id, int64_t now)
	{
		if(id != target || now - lastHit >= RIFT_COMBO_TIMEOUT_MS || now < lastHit)
			reset();
		target = id;
		lastHit = now;
		if(++hits < 3)
			return false;
		reset();
		return true;
	}
};

inline int gravitonDamage(int armor, bool pvp)
{
	int extra = GRAVITON_BASE_DAMAGE + std::max(0, std::min(armor, int(GRAVITON_ARMOR_CAP))) / 2;
	return pvp ? extra / 2 : extra;
}

inline int aetherManaGain(int64_t healthDamage, int64_t missingMana, bool pvp)
{
	if(healthDamage <= 0 || missingMana <= 0)
		return 0;
	const int cap = pvp ? AETHER_MANA_CAP / 2 : AETHER_MANA_CAP;
	return std::min<int64_t>(missingMana,
		std::min<int64_t>(cap, std::max<int64_t>(1, healthDamage * AETHER_MANA_PERCENT / 100)));
}

#endif
