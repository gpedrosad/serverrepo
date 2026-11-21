// Frost Mine: visible blue fire, bought from Dark Rodo, single-trigger player damage.
// Runtime state belongs to the trap, not to Player/Creature. See docs/gameplay/FROST_MINE.md.
#include "definitions.h"
#include <algorithm>
#include <map>
#include <boost/bind.hpp>
#include "frost_mine.h"
#include "game.h"
#include "player.h"
#include "tile.h"
#include "magic.h"
#include "luascript.h"

extern LuaScript g_config;

namespace {
const long ARM_MS = 1000;
const long LIFETIME_MS = 30000;
const unsigned int MAX_MINES = 3;

struct MineState {
	unsigned long ownerId;
	int64_t armedAt;
};
std::map<MagicEffectItem*, MineState> mines;

bool safeTile(const Tile* tile)
{
	return !tile || !tile->ground || tile->isPz() || tile->isHouse() || tile->isTrainingArea();
}

bool removeMine(Game* game, MagicEffectItem* mine)
{
	mines.erase(mine);
	if(mine->isRemoved || !game->removeThing(NULL, mine->pos, mine))
		return false;
	game->FreeThing(mine); // map reference; the expiry event still owns a reference
	return true;
}

void expireMine(Game* game, MagicEffectItem* mine)
{
	OTSYS_THREAD_LOCK_CLASS lockClass(game->gameLock, "expireFrostMine()");
	removeMine(game, mine);
	game->FreeThing(mine); // expiry event reference, also after detonation or Destroy Field
}

class MineHit : public MagicEffectTargetClass {
public:
	explicit MineHit(unsigned long victim) : victimId(victim)
	{
		minDamage = 180;
		maxDamage = 240; // normal player-vs-player reduction gives 90-120 before equipment
		offensive = true;
		attackType = ATTACK_FIRE;
		damageEffect = 26; // NM_ME_ICE_HIT: native fire hit recolored blue
		hitEffect = 27; // NM_ME_ICE_EXPLOSION
		animationColor = 0x71;
	}

	bool causeExhaustion(bool) const override { return false; }
	int64_t getDamage(Creature* target, const Creature* attacker = NULL) const override
	{
		if(!target || target->getID() != victimId || !dynamic_cast<Player*>(target))
			return 0;
		return MagicEffectTargetClass::getDamage(target, attacker);
	}
private:
	unsigned long victimId;
};
}

bool placeFrostMine(Game* game, Player* owner, const Position& pos)
{
	if(!game || !owner)
		return false;
	OTSYS_THREAD_LOCK_CLASS lockClass(game->gameLock, "placeFrostMine()");
	Tile* from = game->getTile(owner->pos);
	Tile* tile = game->getTile(pos);
	if(game->getWorldType() == WORLD_TYPE_NO_PVP || owner->isRookie() ||
		safeTile(from) || safeTile(tile)) {
		owner->sendCancel("Frost Mine can only be used in PvP outside protected areas.");
		return false;
	}
	if(owner->pos.z != pos.z || std::abs(owner->pos.x - pos.x) > 4 ||
		std::abs(owner->pos.y - pos.y) > 4 ||
		game->canThrowObjectTo(owner->pos, pos, BLOCK_PROJECTILE) != RET_NOERROR) {
		owner->sendCancel("You cannot throw there.");
		return false;
	}
	if(tile->getTopCreature() || tile->getFieldItem() || tile->floorChange() ||
		tile->getTeleportItem() || tile->isBlocking(BLOCK_SOLID, true) != RET_NOERROR) {
		owner->sendCancel("Place the mine on an empty, walkable tile without a field.");
		return false;
	}
	unsigned int active = 0;
	for(auto it = mines.begin(); it != mines.end(); ++it)
		if(it->second.ownerId == owner->getID() && !it->first->isRemoved)
			++active;
	if(active >= MAX_MINES) {
		owner->sendCancel("You already have 3 active Frost Mines.");
		return false;
	}
	TransformMap transforms;
	transforms[ITEM_FROST_MINE_FIRE] = TransformItem(0, ConditionVec());
	MagicEffectItem* mine = new MagicEffectItem(transforms);
	mine->useThing();
	game->addThing(NULL, pos, mine);
	mine->isRemoved = false;
	mines[mine] = MineState{owner->getID(), OTSYS_TIME() + ARM_MS};
	mine->useThing();
	game->addEvent(makeTask(LIFETIME_MS, boost::bind(&expireMine, game, mine)));
	owner->pzLocked = true;
	owner->inFightTicks = std::max(g_config.PZ_LOCKED, owner->inFightTicks);
	owner->sendIcons();
	owner->sendTextMessage(MSG_SMALLINFO, "Frost Mine placed. It arms in 1 second and lasts 30 seconds.");
	game->sendMagicEffect(pos, NM_ME_MAGIC_ENERGIE);
	return true;
}

void triggerFrostMine(Game* game, Creature* creature)
{
	Player* victim = dynamic_cast<Player*>(creature);
	if(!game || !victim || victim->isRemoved || victim->isGmProtected())
		return;
	OTSYS_THREAD_LOCK_CLASS lockClass(game->gameLock, "triggerFrostMine()");
	Tile* tile = game->getTile(victim->pos);
	MagicEffectItem* mine = tile ? tile->getFieldItem() : NULL;
	auto it = mines.find(mine);
	if(it == mines.end() || mine->isRemoved || OTSYS_TIME() < it->second.armedAt)
		return;
	Player* owner = game->getPlayerByID(it->second.ownerId);
	if(!owner || owner->isRemoved || owner->health <= 0 || game->getWorldType() == WORLD_TYPE_NO_PVP ||
		owner->pos.z != victim->pos.z || safeTile(game->getTile(owner->pos)) || safeTile(tile)) {
		removeMine(game, mine);
		return;
	}
	if(owner == victim || victim->isRookie() ||
		(owner->party != 0 && owner->party == victim->party))
		return;
	// Remove before damage: death/teleport callbacks cannot detonate the same trap twice.
	if(!removeMine(game, mine))
		return;
	MineHit hit(victim->getID());
	game->creatureMakeMagic(owner, victim->pos, &hit);
}
