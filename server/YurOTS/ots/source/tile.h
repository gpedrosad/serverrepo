//////////////////////////////////////////////////////////////////////
// OpenTibia - an opensource roleplaying game
//////////////////////////////////////////////////////////////////////
// a Tile represents a single field on the map.
// it is a list of Items
//////////////////////////////////////////////////////////////////////
// This program is free software; you can redistribute it and/or
// modify it under the terms of the GNU General Public License
// as published by the Free Software Foundation; either version 2
// of the License, or (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program; if not, write to the Free Software Foundation,
// Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
//////////////////////////////////////////////////////////////////////

#ifndef __TILE_H__
#define __TILE_H__

#include "item.h"
#include "container.h"
#include "magic.h"

#include "definitions.h"
#include "templates.h"
#include "scheduler.h"

class Creature;
class House;

typedef std::vector<Item*> ItemVector;
typedef std::vector<Creature*> CreatureVector;

class Tile
{
public:
  Creature* getCreature() const{
		if(creatures.size())
			return creatures[0];
		else
			return NULL;
  }

  Tile()
  {
    pz     = false;
    splash = NULL;
		ground = NULL;

	house = NULL;

	pvpArena = false;

	trainingArea = false;
  }

  Item*          ground;
  Item*          splash;
  ItemVector     topItems;
  CreatureVector creatures;
  ItemVector     downItems;

	bool isHouse() const;
	House* getHouse() const;
	bool setHouse(House* newHouse);

	bool isPvpArena() const;
	void setPvpArena(const Position& exit);
	Position getPvpArenaExit() const;

	bool isTrainingArea() const;
	void setTrainingArea(const Position& exit);
	Position getTrainingExit() const;

	long clean();

	long getItemHoldingCount() const;

  bool removeThing(Thing *thing);
  void addThing(Thing *thing);
	bool insertThing(Thing *thing, int stackpos);
	MagicEffectItem* getFieldItem();
	Teleport* getTeleportItem() const;

	Thing* getTopMoveableThing();
	Creature* getTopCreature();
	Item* getTopTopItem();
	Item* getTopDownItem();
	Item* getMoveableBlockingItem();

  int getCreatureStackPos(Creature *c) const;
  int getThingStackPos(const Thing *thing) const;
	int getThingCount() const;

  Thing* getTopThing();
	Thing* getThingByStackPos(int pos);

	ReturnValue isBlocking(int objectstate, bool ignoreCreature = false, bool ignoreMoveableBlocking = false) const;

  bool isPz() const;
  void setPz();

  bool floorChange() const;
  bool floorChangeDown() const;
  bool floorChange(Direction direction) const;

  std::string getDescription() const;

protected:
  bool pz;

	House* house;

	bool pvpArena;
	Position arenaExit;

	bool trainingArea;
	Position trainingExit;
};

#endif // #ifndef __TILE_H__
