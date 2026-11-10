//////////////////////////////////////////////////////////////////////
// OpenTibia - an opensource roleplaying game
//////////////////////////////////////////////////////////////////////
// class which takes care of all data which must get saved in the player
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


#ifndef __LUASCRIPT_H__
#define __LUASCRIPT_H__

#include <string>
#include "definitions.h"
extern "C"
{
#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>
}

extern "C" struct lua_State;

typedef __int64 exp_t;

class LuaScript
{
public:
	LuaScript();
	~LuaScript();

	exp_t EXP_MUL;
	exp_t EXP_MUL_PVP;
	int LOOT_MUL;
	int GOLD_LOOT_FLOOR_PERCENT;
	int SOUL_MAX;
	int SOUL_REGEN_TICKS;
	int64_t HEALTH_TICK_MUL;
	int64_t MANA_TICK_MUL;
	int64_t CAP_GAIN[5];
	int START_CAP;
	int START_CAP_LEVEL;
	int64_t MANA_GAIN[5];
	int64_t HP_GAIN[5];
	int WEAPON_MUL[5];
	int SHIELD_MUL[5];
	int DIST_MUL[5];
	int64_t MANA_MUL[5];

	static const int MAX_EXP_TIERS = 4;
	int EXP_TIER_MIN[MAX_EXP_TIERS];
	int EXP_TIER_MAX[MAX_EXP_TIERS];
	exp_t EXP_TIER_MUL[MAX_EXP_TIERS];
	int EXP_TIER_COUNT;

	exp_t getExpMulForLevel(int level) const;


	bool LEARN_SPELLS;

	int ACCESS_HOUSE;
	int MAX_HOUSE_TILE_ITEMS;

	bool  SUMMONS_ALL_VOC;
	size_t MAX_SUMMONS;

	int HIT_TIME;
	int WHITE_TIME;
	int RED_TIME;
	int FRAG_TIME;
	int RED_UNJUST;
	int BAN_UNJUST;

	double BURST_DMG_LVL;
	double BURST_DMG_MLVL;
	double BURST_DMG_LO;
	double BURST_DMG_HI;

	bool CAP_SYSTEM;

	int SPEAR_LOSE_CHANCE;

	bool FREE_PREMMY;
	bool QUEUE_PREMMY;
	int PREMMY_EXP_BONUS;
	int PREMMY_LOOT_BONUS;
	int PREMMY_SKILL_MUL;

	int TRAINING_DAILY_MINUTES;
	int TRAINING_PREMIUM_MINUTES;

	std::string VOCATIONS[5];
	std::string PROMOTED_VOCATIONS[5];
	int DIE_PERCENT_EXP;
	int64_t DIE_PERCENT_MANA;
	int DIE_PERCENT_SKILL;
	int DIE_PERCENT_EQ;
	int DIE_PERCENT_BP;
	bool PVP_UNDERDOG_EXP;
	int PVP_UNDERDOG_EXP_PERCENT;
	int PVP_UNDERDOG_EXP_MIN_DIFF;
	int PVP_UNDERDOG_EXP_MIN_LEVEL;
	long PZ_LOCKED;
	long EXHAUSTED;
	long EXHAUSTED_ADD;
	long EXHAUSTED_HEAL;
	int ACCESS_PROTECT;
	int ACCESS_REMOTE;
	int ACCESS_TALK;
	int ACCESS_ENTER;
	int ACCESS_LOOK;
	int MAX_DEPOT_ITEMS;
	std::string DATA_DIR;

	size_t MAX_DEATH_ENTRIES;

	int64_t MANA_SNAKEBITE;
	int64_t MANA_MOONLIGHT;
	int64_t MANA_VOLCANIC;
	int64_t MANA_QUAGMIRE;
	int64_t MANA_TEMPEST;

	int64_t MANA_VORTEX;
	int64_t MANA_DRAGONBREATH;
	int64_t MANA_PLAGUE;
	int64_t MANA_COSMIC;
	int64_t MANA_INFERNO;

	int RANGE_SNAKEBITE;
	int RANGE_MOONLIGHT;
	int RANGE_VOLCANIC;
	int RANGE_QUAGMIRE;
	int RANGE_TEMPEST;

	int RANGE_VORTEX;
	int RANGE_DRAGONBREATH;
	int RANGE_PLAGUE;
	int RANGE_COSMIC;
	int RANGE_INFERNO;

	double WAND_ML_FACTOR;

	bool ACCMAKER;
	bool ACCMAKER_ROOK;

  int OpenFile(const char* file);
  int getField (const char *key);
  void setField (const char *index, int value);
  //static version
  static int getField (lua_State *L , const char *key);
  static void setField (lua_State *L, const char *index, int val);
  // get a global string
  std::string getGlobalString(std::string var, const std::string &defString = "");
  int getGlobalNumber(std::string var, const int defNum = 0);
  std::string getGlobalStringField (std::string var, const int key, const std::string &defString = "");
  // set a var to a val
  int setGlobalString(std::string var, std::string val);
  int setGlobalNumber(std::string var, int val);

protected:
	std::string luaFile;   // the file we represent
	lua_State*  luaState;  // our lua state
};


#endif  // #ifndef __LUASCRIPT_H__
