#include <cassert>
#include <iostream>
#include "../../server/YurOTS/ots/source/melee_relics.h"

int main()
{
	RiftCombo combo;
	assert(!combo.advance(7, 10000));
	assert(!combo.advance(7, 11200));
	assert(combo.advance(7, 12400));
	assert(!combo.advance(7, 13600));
	assert(!combo.advance(8, 14800)); // target change cannot keep a charge
	assert(!combo.advance(8, 16000));
	assert(combo.advance(8, 17200));
	assert(!combo.advance(9, 20000));
	assert(!combo.advance(9, 21200));
	assert(!combo.advance(9, 27200)); // exact timeout, not just greater than it
	assert(combo.hits == 1);
	combo.reset(); // miss, unequip or cancel attack
	assert(combo.hits == 0 && combo.target == 0);
	assert(!combo.advance(9, 30000));
	assert(!combo.advance(9, 29999)); // clock reversal also discards a charge
	assert(combo.hits == 1);
	assert(gravitonDamage(-10, false) == 12);
	assert(gravitonDamage(20, false) == 22);
	assert(gravitonDamage(60, false) == 42);
	assert(gravitonDamage(600, false) == 42);
	assert(gravitonDamage(60, true) == 21);
	assert(aetherManaGain(0, 100, false) == 0); // full mana-shield hit or block
	assert(aetherManaGain(-1, 100, false) == 0);
	assert(aetherManaGain(100, 0, false) == 0);
	assert(aetherManaGain(100, -1, false) == 0);
	assert(aetherManaGain(1, 100, false) == 1);
	assert(aetherManaGain(50, 100, false) == 6);
	assert(aetherManaGain(10000, 100, false) == 10);
	assert(aetherManaGain(10000, 100, true) == 5);
	assert(aetherManaGain(10000, 2, false) == 2);
	assert(isMeleeRelic(20225) && isMeleeRelic(20226) && isMeleeRelic(20227));
	assert(!isMeleeRelic(20211) && !isMeleeRelic(2407));
	std::cout << "PASS: combo/target/timeout/reset, armor caps, PvP and actual-health mana gain\n";
}
