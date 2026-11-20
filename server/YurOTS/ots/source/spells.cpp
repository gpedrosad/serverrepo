//////////////////////////////////////////////////////////////////////
// OpenTibia - an opensource roleplaying game
//////////////////////////////////////////////////////////////////////
//
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

#include "definitions.h"

#include <algorithm>
#include <functional>
#include <string>
#include <fstream>
#include <sstream>
#include <vector>
#include <set>
#include <map>

#include <libxml/xmlmemory.h>
#include <libxml/parser.h>

#include <boost/config.hpp>
#include <boost/bind.hpp>

#include "spells.h"
#include "exhaust.h"
#include "spellcooldown.h"
#include "playerstates.h"
#include "monster.h"
#include "player.h"
#include "tile.h"
#include "items.h"
#include "item.h"
#include "const76.h"
#include "summons.h"

extern Spells spells;

extern LuaScript g_config;

// Estados de combate consultados desde game.cpp (ver playerstates.h).
std::map<unsigned long, CounterStanceState> g_counterStance;

namespace {

bool isLegacyDesintegrateTarget(unsigned short itemid)
{
	return
		(itemid == 1497 || itemid == 1498) ||
		(itemid >= 3805 && itemid <= 3810) ||
		(itemid >= 1646 && itemid <= 1661) ||
		(itemid >= 1666 && itemid <= 1677) ||
		(itemid >= 3813 && itemid <= 3820) ||
		(itemid >= 1714 && itemid <= 1717) ||
		(itemid >= 1724 && itemid <= 1737) ||
		itemid == 1738 || itemid == 1739 || itemid == 1741 ||
		(itemid >= 1750 && itemid <= 1753) ||
		(itemid >= 2080 && itemid <= 2085) ||
		(itemid >= 2116 && itemid <= 2119) ||
		(itemid >= 2581 && itemid <= 2588) ||
		itemid == 2095 || itemid == 2098 || itemid == 2101 ||
		itemid == 2104 || itemid == 2105 || itemid == 1775 ||
		itemid == 2602 || itemid == 1619 || itemid == 2064 ||
		(itemid >= 1614 && itemid <= 1616);
}

void sendSpellMagicEffect(Game* game, const Position& pos, int type)
{
	game->sendMagicEffect(pos, type);
}

// Avisos de los hechizos de nov 2026 (exeta sio, exana res, exori vis con, exura tera, exevo vis tera,
// utito tera, utamo mort). Los que dicen "for N s." / "in N s." y los de fin los lee el cliente para el
// ícono con la cuenta regresiva (modules/game_inventory/inventory.lua de clienteretro): no cambiar esos
// textos sin cambiar el cliente. Doc: docs/gameplay/SPELLS_FEEDBACK.md.
void sendSpellText(Creature* creature, MessageClasses mclass, const std::string& text)
{
	Player* player = dynamic_cast<Player*>(creature);
	if(player)
		player->sendTextMessage(mclass, text.c_str());
}

long spellSeconds(long ms)
{
	return ms <= 0 ? 0 : (ms + 999) / 1000;
}

// El hechizo no hizo nada (en espera, sin blanco, sin monstruos...): polvo sobre el jugador, que lo ven
// todos, como cuando falla un hechizo en 7.6, y el motivo abajo.
void spellFail(Game* game, Creature* creature, const std::string& text)
{
	if(!creature)
		return;
	game->sendMagicEffect(creature->pos, NM_ME_PUFF);
	sendSpellText(creature, MSG_SMALLINFO, text);
}

// Nombre del hechizo para mostrar: el server los guarda en minúscula ("counter stance" -> "Counter Stance").
std::string spellTitle(std::string name)
{
	bool start = true;
	for(size_t i = 0; i < name.size(); ++i) {
		if(start && name[i] >= 'a' && name[i] <= 'z')
			name[i] = name[i] - 'a' + 'A';
		start = (name[i] == ' ');
	}
	return name;
}

// Evento: manda `text` a la criatura `id` si sigue en el juego.
void sendSpellTextLater(Game* game, unsigned long id, std::string text)
{
	sendSpellText(game->getCreatureByID(id), MSG_SMALLINFO, text);
}

// Evento: termina la postura de contraataque si sigue siendo la misma (no la de un cast posterior).
void endCounterStance(Game* game, unsigned long id, int64_t until)
{
	std::map<unsigned long, CounterStanceState>::iterator it = g_counterStance.find(id);
	if(it == g_counterStance.end() || it->second.until != until)
		return;
	g_counterStance.erase(it);
	sendSpellText(game->getCreatureByID(id), MSG_SMALLINFO, "Your counter stance ends.");
}

// ---------- Eco (utevo vis) ----------
// Estado por jugador (id de criatura): hasta cuándo está activo, desde cuándo se puede volver a lanzar y
// cuánto pega la repetición. Lo llena startEcho (los números vienen del Lua) y lo consume onPlayerSpellCast.
struct EchoState {
	int64_t activeUntil;
	int64_t readyAt;
	double scale;
	double pvpScale;
	EchoState() : activeUntil(0), readyAt(0), scale(0.5), pvpScale(0.25) {}
};
static std::map<unsigned long, EchoState> echoStates;
static const int64_t ECHO_DELAY_MS = 1000;          // la repetición sale 1 s después del golpe
static const int ECHO_EFFECT = 22;                   // NM_ME_SOUND_PURPLE

Item* getTopDesintegrateItem(Tile* tile)
{
	if(!tile)
		return NULL;

	const int thingCount = tile->getThingCount();
	for(int stackpos = 1; stackpos < thingCount; ++stackpos) {
		Item* item = dynamic_cast<Item*>(tile->getThingByStackPos(stackpos));
		if(item && isLegacyDesintegrateTarget(item->getID()))
			return item;
	}

	return NULL;
}

bool removeTileItem(Game* game, Creature* caster, Item* item)
{
	if(!game || !item)
		return false;

	Player* player = dynamic_cast<Player*>(caster);
	if(game->removeThing(player, item->pos, item)) {
		game->FreeThing(item);
		return true;
	}

	return false;
}

}

// Shared exhaust for bindings that skip creatureMakeMagic (Paralyze, Anchor, etc.).
// healStyle=true → exhaustedheal (support); false → exhausted (offensive).
static bool playerSpellExhaustBlocked(Player* player)
{
	if(!player || player->access >= g_config.ACCESS_PROTECT)
		return false;
	if(!PlayerExhaust::isExhausted(player))
		return false;
	player->sendTextMessage(MSG_SMALLINFO, "You are exhausted.", player->pos, NM_ME_PUFF);
	return true;
}

static void applyPlayerSpellExhaust(Player* player, bool healStyle)
{
	if(!player || player->access >= g_config.ACCESS_PROTECT)
		return;
	PlayerExhaust::set(player, healStyle ? g_config.EXHAUSTED_HEAL : g_config.EXHAUSTED);
}

Spells::Spells(Game* igame): game(igame){

                   }

bool Spells::loadFromXml(const std::string &datadir)
{
	std::string name, words;
  bool enabled = false;
  int64_t vocId, maglv = 0, mana = 0, id = 0, charges = 0;
  this->loaded = false;

	std::string filename = datadir + "spells/spells.xml";
	std::transform(filename.begin(), filename.end(), filename.begin(), tolower);
  xmlDocPtr doc = xmlParseFile(filename.c_str());

  if (doc){
		this->loaded=true;
		xmlNodePtr root, p, tmp;
		char* nodeValue = NULL;
		root = xmlDocGetRootElement(doc);

		if (xmlStrcmp(root->name,(const xmlChar*) "spells")){
			//TODO: use exceptions here
			std::cerr << "Malformed XML" << std::endl;
		}

		nodeValue = (char*)xmlGetProp(root, (const xmlChar *)"maxVoc");
		if(nodeValue) {
			maxVoc = atoll(nodeValue);
			xmlFreeOTSERV(nodeValue);
		}

		for(int i =0; i<=this->maxVoc; i++){
			std::map<std::string, Spell*> voc;
			vocationSpells.push_back(voc);
		}

		p = root->children;

		while (p)
		{
			const char* str = (char*)p->name;

			if (strcmp(str, "spell") == 0){
				nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"enabled");
				if(nodeValue) {
					enabled = (bool)(atoi(nodeValue) > 0);
					xmlFreeOTSERV(nodeValue);
				}

				if (enabled){
					nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"name");
					if(nodeValue) {
						name = nodeValue;
						xmlFreeOTSERV(nodeValue);
						std::transform(name.begin(), name.end(), name.begin(), tolower);
					}

					nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"words");
					if(nodeValue) {
						words = nodeValue;
						xmlFreeOTSERV(nodeValue);
					}

					nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"maglv");
					if(nodeValue) {
						maglv = atoll(nodeValue);
						xmlFreeOTSERV(nodeValue);
					}

					nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"mana");
					if(nodeValue) {
						mana = atoll(nodeValue);
						xmlFreeOTSERV(nodeValue);
					}

					Spell* spell = new InstantSpell(datadir, name, words, maglv, mana, game);

					nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"echo");
					if(nodeValue) {
						spell->setEchoable(atoi(nodeValue) > 0);
						xmlFreeOTSERV(nodeValue);
					}

					tmp=p->children;
					while (tmp){
						if (strcmp((const char*)tmp->name, "vocation") == 0){
							nodeValue = (char*)xmlGetProp(tmp, (const xmlChar *)"id");
							if(nodeValue) {
								vocId = atoi(nodeValue);
								xmlFreeOTSERV(nodeValue);

								if (vocId<=this->maxVoc){
									(vocationSpells.at(vocId))[words] = spell;
								}
							}
						}

						tmp = tmp->next;
					}

					allSpells[words] = spell;
				}
			}
			else if (strcmp(str, "rune") == 0){
				nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"enabled");
				if(nodeValue) {
					enabled = (bool)(atoi(nodeValue) > 0);
					xmlFreeOTSERV(nodeValue);
				}

				if (enabled){
					nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"name");
					if(nodeValue) {
						name = nodeValue;
						xmlFreeOTSERV(nodeValue);
						std::transform(name.begin(), name.end(), name.begin(), tolower);
					}

					nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"id");
					if(nodeValue) {
						id = atoi(nodeValue);
						xmlFreeOTSERV(nodeValue);
					}

					nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"charges");
					if(nodeValue) {
						charges = atoi(nodeValue);
						xmlFreeOTSERV(nodeValue);
					}

					nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"maglv");
					if(nodeValue) {
						maglv = atoll(nodeValue);
						xmlFreeOTSERV(nodeValue);
					}

					nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"mana");
					if(nodeValue) {
						mana = atoll(nodeValue);
						xmlFreeOTSERV(nodeValue);
					}

					Spell* spell = new RuneSpell(datadir, name, id, charges, maglv, mana, game);

					tmp=p->children;
					while (tmp){
						if (strcmp((const char*)tmp->name, "vocation") == 0){
							nodeValue = (char*)xmlGetProp(tmp, (const xmlChar *)"id");
							if(nodeValue) {
								vocId = atoi(nodeValue);
								xmlFreeOTSERV(nodeValue);

								if (vocId<=this->maxVoc){
									(vocationRuneSpells.at(vocId))[id] = spell;
								}
							}
						}

						tmp = tmp->next;
					}

					allRuneSpells[id] = spell;
				}
			}

			p = p->next;
		}

		xmlFreeDoc(doc);
	}

  return this->loaded;
}
Spells::~Spells(){
	std::map<std::string, Spell*>::iterator it = allSpells.begin();

	while(it != allSpells.end()) {
		delete it->second;
		allSpells.erase(it);
		it = allSpells.begin();
	}
}

Spell::Spell(std::string iname, int64_t imagLv, int64_t imana, Game* igame)
:  game(igame), name(iname),magLv(imagLv) , mana(imana)
{
	this->loaded=false;
	this->echoable=false;
	this->script = NULL;
}

Spell::~Spell(){
	if(script) {
		delete script;
		script = NULL;
	}
}

InstantSpell::InstantSpell(const std::string &datadir, std::string iname, std::string iwords, int64_t magLv, int64_t mana, Game* game)
: Spell(iname, magLv, mana, game), words(iwords)
{
	this->script = new SpellScript(datadir, std::string(datadir + "spells/instant/")+(this->words)+std::string(".lua"), this);
	// Spell starts loaded=false; set true only when the Lua script actually loaded.
	this->loaded = this->script && this->script->isLoaded();
}

RuneSpell::RuneSpell(const std::string &datadir, std::string iname, unsigned short id, unsigned short charges, int64_t magLv, int64_t mana, Game* game)
: Spell(iname, magLv, mana, game)
{
	this->id = id;
	this->charges = charges;

	this->script = new SpellScript(datadir, std::string(datadir + "spells/runes/")+(this->name)+std::string(".lua"), this);
	this->loaded = this->script && this->script->isLoaded();
}

SpellScript::SpellScript(const std::string &datadir, std::string scriptname, Spell* spell){
	this->loaded = false;
	this->spell = spell;
	if(scriptname == "")
		return;
	luaState = lua_open();
	luaL_openlibs(luaState);
    lua_dofile(luaState, std::string(datadir + "spells/lib/spells.lua").c_str());

	FILE* in=fopen(scriptname.c_str(), "r");

	if(!in)
		return;
	else
		fclose(in);
	lua_dofile(luaState, scriptname.c_str());
	this->loaded=true;
	this->spell=spell;
	lua_pushlightuserdata(luaState, spell);
	lua_setglobal(luaState, "addressOfSpell");
	this->registerFunctions();
}

int SpellScript::registerFunctions(){

	lua_register(luaState, "doTargetMagic", SpellScript::luaActionDoTargetSpell);
	lua_register(luaState, "doTargetExMagic", SpellScript::luaActionDoTargetExSpell);
	lua_register(luaState, "doTargetGroundMagic", SpellScript::luaActionDoTargetGroundSpell);
	lua_register(luaState, "doAreaMagic", SpellScript::luaActionDoAreaSpell);
	lua_register(luaState, "doAreaAnimation", SpellScript::luaActionDoAreaAnimation);
	lua_register(luaState, "doAreaExMagic", SpellScript::luaActionDoAreaExSpell);
	lua_register(luaState, "doAreaGroundMagic", SpellScript::luaActionDoAreaGroundSpell);

	lua_register(luaState, "changeOutfit", SpellScript::luaActionChangeOutfit);
	lua_register(luaState, "manaShield", SpellScript::luaActionManaShield);
	lua_register(luaState, "getPosition", SpellScript::luaActionGetPos);
	lua_register(luaState, "getAttackedCreaturePos", SpellScript::luaActionGetAttackedCreaturePos);
	lua_register(luaState, "getPlayerSkill", SpellScript::luaActionGetPlayerSkill);
	lua_register(luaState, "getPlayerWeapon", SpellScript::luaActionGetPlayerWeapon);
	lua_register(luaState, "getCreatureDirection", SpellScript::luaActionGetCreatureDirection);
	lua_register(luaState, "echoReady", SpellScript::luaActionEchoReady);
	lua_register(luaState, "startEcho", SpellScript::luaActionStartEcho);
	lua_register(luaState, "attackSpeedReady", SpellScript::luaActionAttackSpeedReady);
	lua_register(luaState, "startAttackSpeed", SpellScript::luaActionStartAttackSpeed);
	lua_register(luaState, "getSpeed", SpellScript::luaActionGetSpeed);
	lua_register(luaState, "changeSpeed", SpellScript::luaActionChangeSpeed);
	lua_register(luaState, "changeSpeedMonster", SpellScript::luaActionChangeSpeedMonster);
	lua_register(luaState, "makeRune", SpellScript::luaActionMakeRune);
	lua_register(luaState, "makeArrows", SpellScript::luaActionMakeArrows);
	lua_register(luaState, "makeFood", SpellScript::luaActionMakeFood);
	lua_register(luaState, "reduceExhaustion", SpellScript::luaActionReduceExhaustion);
	lua_register(luaState, "reduceExhaustionByPercent", SpellScript::luaActionReduceExhaustionByPercent);
	lua_register(luaState, "skillBuff", SpellScript::luaActionSkillBuff);
	lua_register(luaState, "doDesintegrate", SpellScript::luaActionDoDesintegrate);
	lua_register(luaState, "doAnchorRoot", SpellScript::luaActionDoAnchorRoot);
	lua_register(luaState, "doCrimsonCage", SpellScript::luaActionDoCrimsonCage);
	lua_register(luaState, "doCurePoison", SpellScript::luaActionDoCurePoison);
	lua_register(luaState, "doAnimateDead", SpellScript::luaActionDoAnimateDead);
	lua_register(luaState, "doConvinceCreature", SpellScript::luaActionDoConvinceCreature);
	lua_register(luaState, "doChameleon", SpellScript::luaActionDoChameleon);
	lua_register(luaState, "doParalyze", SpellScript::luaActionDoParalyze);
	lua_register(luaState, "doChallenge", SpellScript::luaActionDoChallenge);

	// Cooldowns propios por hechizo.
	lua_register(luaState, "spellCooldownReady", SpellScript::luaActionSpellCooldownReady);
	lua_register(luaState, "setSpellCooldown", SpellScript::luaActionSetSpellCooldown);

	// Nuevos spells (nov 2026).
	lua_register(luaState, "doRescue", SpellScript::luaActionDoRescue);
	lua_register(luaState, "doCleanse", SpellScript::luaActionDoCleanse);
	lua_register(luaState, "doChainLightning", SpellScript::luaActionDoChainLightning);
	lua_register(luaState, "doDelayedHeal", SpellScript::luaActionDoDelayedHeal);
	lua_register(luaState, "doDetonateFields", SpellScript::luaActionDoDetonateFields);
	lua_register(luaState, "doCounterStance", SpellScript::luaActionDoCounterStance);
	lua_register(luaState, "doBloodRitual", SpellScript::luaActionDoBloodRitual);

	lua_register(luaState, "setPlayerLightLevel", SpellScript::luaSetPlayerLightLevel);
	lua_register(luaState, "invisible", SpellScript::luaActionInvisible);

	return true;
}

bool SpellScript::safeCast(Spell* spell, Creature* creature, const Position& pos, const std::string& var)
{
	// Guard only the script pointer/load state. Missing/broken Lua must fail soft
	// (no crash); do not rely solely on Spell::loaded for the cast path.
	if(!spell)
		return false;

	SpellScript* script = spell->getSpellScript();
	if(!script || !script->isLoaded())
		return false;

	return script->castSpell(creature, pos, var);
}

bool SpellScript::castSpell(Creature* creature, const Position& pos, std::string var){
	if(!spell) {
		std::cout << "SpellScript::castSpell: spell pointer is null" << std::endl;
		return false;
	}
	if(!loaded || !luaState) {
		std::cout << "SpellScript::castSpell: script not loaded for spell " << spell->getName() << std::endl;
		return false;
	}

	lua_pushstring(luaState, "onCast");
	lua_gettable(luaState, LUA_GLOBALSINDEX);
	if(!lua_isfunction(luaState, -1)) {
		std::cout << "SpellScript::castSpell: onCast missing for spell " << spell->getName() << std::endl;
		lua_pop(luaState, 1);
		return false;
	}
	lua_pushnumber(luaState, creature->getID());

	lua_newtable(luaState);
	setField("z", pos.z);
	setField("y", pos.y);
	setField("x", pos.x);

	lua_pushnumber(luaState, creature->level);
	lua_pushnumber(luaState, creature->maglevel);
	lua_pushstring(luaState, var.c_str());

	if(lua_pcall(luaState, 5, 1, 0) != 0) {
		const char* error = lua_tostring(luaState, -1);
		std::cout << "SpellScript::castSpell error in " << spell->getName() << ": "
			<< (error ? error : "unknown lua error") << std::endl;
		lua_pop(luaState, 1);
		return false;
	}

	bool ret = (bool)(lua_toboolean(luaState, -1) > 0);
	lua_pop(luaState, 1);

	return ret;
}

int SpellScript::luaActionDoDesintegrate(lua_State *L)
{
	Position pos;
	internalGetPosition(L, pos);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* creature = spell->game->getCreatureByID(cid);
	if(!creature) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Player* casterPlayer = dynamic_cast<Player*>(creature);
	if(playerSpellExhaustBlocked(casterPlayer)) {
		lua_pushnumber(L, 0);
		return 1;
	}

	if(creature->pos.z != pos.z) {
		creature->sendCancel("You need to be on the same floor.");
		lua_pushnumber(L, 0);
		return 1;
	}

	if(spell->game->canThrowObjectTo(creature->pos, pos, BLOCK_PROJECTILE) != RET_NOERROR) {
		creature->sendCancel("You cannot throw there.");
		lua_pushnumber(L, 0);
		return 1;
	}

	Tile* tile = spell->game->getTile(pos);
	if(!tile) {
		sendSpellMagicEffect(spell->game, creature->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	MagicEffectItem* fieldItem = tile->getFieldItem();
	if(fieldItem && (fieldItem->getID() == 1497 || fieldItem->getID() == 1498)) {
		bool removed = removeTileItem(spell->game, creature, fieldItem);
		if(removed) {
			sendSpellMagicEffect(spell->game, pos, NM_ME_PUFF);
			applyPlayerSpellExhaust(casterPlayer, true);
		}
		lua_pushnumber(L, removed ? 1 : 0);
		return 1;
	}

	Item* item = getTopDesintegrateItem(tile);
	if(item) {
		bool removed = removeTileItem(spell->game, creature, item);
		if(removed) {
			sendSpellMagicEffect(spell->game, pos, NM_ME_PUFF);
			applyPlayerSpellExhaust(casterPlayer, true);
		}
		lua_pushnumber(L, removed ? 1 : 0);
		return 1;
	}

	sendSpellMagicEffect(spell->game, creature->pos, NM_ME_PUFF);
	lua_pushnumber(L, 0);
	return 1;
}

int SpellScript::luaActionDoAnchorRoot(lua_State *L)
{
	const long ANCHOR_ROOT_MS = 1000;

	Position pos;
	internalGetPosition(L, pos);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* creature = spell->game->getCreatureByID(cid);
	if(!creature) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Player* caster = dynamic_cast<Player*>(creature);
	if(playerSpellExhaustBlocked(caster)) {
		lua_pushnumber(L, 0);
		return 1;
	}

	if(creature->pos.z != pos.z) {
		creature->sendCancel("You need to be on the same floor.");
		lua_pushnumber(L, 0);
		return 1;
	}

	if(spell->game->canThrowObjectTo(creature->pos, pos, BLOCK_PROJECTILE) != RET_NOERROR) {
		creature->sendCancel("You cannot throw there.");
		lua_pushnumber(L, 0);
		return 1;
	}

	Tile* tile = spell->game->getTile(pos);
	if(!tile) {
		sendSpellMagicEffect(spell->game, creature->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* target = tile->getTopCreature();
	if(!target) {
		sendSpellMagicEffect(spell->game, creature->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	if(target == creature) {
		sendSpellMagicEffect(spell->game, creature->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	if(target->access >= g_config.ACCESS_PROTECT) {
		sendSpellMagicEffect(spell->game, creature->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	Player* targetPlayer = dynamic_cast<Player*>(target);
	Tile* fromTile = spell->game->getTile(creature->pos);

	if(caster && caster->access < g_config.ACCESS_PROTECT) {
		if(fromTile && fromTile->isPz()) {
			caster->sendTextMessage(MSG_SMALLINFO, "You may not attack a person while you are in a protection zone.");
			lua_pushnumber(L, 0);
			return 1;
		}
		if(tile->isPz()) {
			caster->sendTextMessage(MSG_SMALLINFO, "You may not attack a person in a protection zone.");
			lua_pushnumber(L, 0);
			return 1;
		}
	}

	// Visual: magic energy hit (not paralyze icon / condition).
	sendSpellMagicEffect(spell->game, target->pos, NM_ME_MAGIC_ENERGIE);

	target->rootTicks = ANCHOR_ROOT_MS;

	if(targetPlayer) {
		targetPlayer->sendTextMessage(MSG_SMALLINFO, "You are rooted.");
		targetPlayer->sendCancelWalk();
	}

	if(caster && targetPlayer && caster->access < g_config.ACCESS_PROTECT &&
		spell->game->getWorldType() != WORLD_TYPE_NO_PVP)
	{
		caster->pzLocked = true;
		caster->inFightTicks = std::max(g_config.PZ_LOCKED, caster->inFightTicks);
		targetPlayer->inFightTicks = std::max(g_config.PZ_LOCKED, targetPlayer->inFightTicks);
		caster->sendIcons();
		targetPlayer->sendIcons();
	}

	applyPlayerSpellExhaust(caster, false);
	lua_pushnumber(L, 1);
	return 1;
}

namespace {

// Crimson Cage Rune: las paredes duran 3 s exactos. No usan startDecay porque el decay avanza de a
// DECAY_INTERVAL (5 s) y 3 s se redondearía a 5; cada pared tiene su propio evento del scheduler.
const long CRIMSON_CAGE_MS = 3000;

// El evento tiene su propia referencia a la pared (useThing), así que si ya no está en el tile
// (la sacó otra cosa) solo suelta esa referencia.
void removeCrimsonCageWall(Game* game, Item* wall)
{
	OTSYS_THREAD_LOCK_CLASS lockClass(game->gameLock, "removeCrimsonCageWall()");

	if(!wall->isRemoved && game->removeThing(NULL, wall->pos, wall))
		game->FreeThing(wall);	// referencia del mapa
	game->FreeThing(wall);		// referencia del evento
}

// Pone una pared en pos. No va en PZ, casas (se guardarían con la casa), tiles con criatura ni
// tiles que ya bloquean (paredes, magic walls, muebles). Un field de fuego/energía/veneno se pisa.
bool placeCrimsonCageWall(Game* game, const Position& pos)
{
	Tile* tile = game->getTile(pos);
	if(!tile || tile->isPz() || tile->isHouse() || tile->getTopCreature())
		return false;
	if(tile->isBlocking(BLOCK_SOLID, true) != RET_NOERROR)
		return false;

	MagicEffectItem* oldField = tile->getFieldItem();
	if(oldField) {
		if(!game->removeThing(NULL, pos, oldField))
			return false;
		game->FreeThing(oldField);
	}

	TransformMap transformMap;
	transformMap[ITEM_CRIMSON_CAGE_WALL] = TransformItem(0, ConditionVec());
	MagicEffectItem* wall = new MagicEffectItem(transformMap);
	wall->useThing();	// referencia del mapa
	game->addThing(NULL, pos, wall);	// la pone en el tile y avisa a los que miran
	wall->isRemoved = false;

	wall->useThing();	// referencia del evento que la saca
	game->addEvent(makeTask(CRIMSON_CAGE_MS, boost::bind(&removeCrimsonCageWall, game, (Item*)wall)));
	return true;
}

}

// doCrimsonCage(cid, pos) — Crimson Cage Rune (20273): paredes rojas en las 8 casillas alrededor del
// blanco durante 3 s. Mismas reglas de blanco que Anchor. Doc: docs/gameplay/CRIMSON_CAGE_RUNE.md.
int SpellScript::luaActionDoCrimsonCage(lua_State *L)
{
	Position pos;
	internalGetPosition(L, pos);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* creature = spell->game->getCreatureByID(cid);
	if(!creature) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Player* caster = dynamic_cast<Player*>(creature);
	if(playerSpellExhaustBlocked(caster)) {
		lua_pushnumber(L, 0);
		return 1;
	}

	if(creature->pos.z != pos.z) {
		creature->sendCancel("You need to be on the same floor.");
		lua_pushnumber(L, 0);
		return 1;
	}

	if(spell->game->canThrowObjectTo(creature->pos, pos, BLOCK_PROJECTILE) != RET_NOERROR) {
		creature->sendCancel("You cannot throw there.");
		lua_pushnumber(L, 0);
		return 1;
	}

	Tile* tile = spell->game->getTile(pos);
	Creature* target = tile ? tile->getTopCreature() : NULL;
	if(!target || target == creature || target->access >= g_config.ACCESS_PROTECT) {
		if(caster)
			caster->sendCancel("You can only use this rune on creatures.");
		sendSpellMagicEffect(spell->game, creature->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	Player* targetPlayer = dynamic_cast<Player*>(target);
	Tile* fromTile = spell->game->getTile(creature->pos);

	if(caster && caster->access < g_config.ACCESS_PROTECT) {
		if(fromTile && fromTile->isPz()) {
			caster->sendTextMessage(MSG_SMALLINFO, "You may not attack a person while you are in a protection zone.");
			lua_pushnumber(L, 0);
			return 1;
		}
		if(tile->isPz()) {
			caster->sendTextMessage(MSG_SMALLINFO, "You may not attack a person in a protection zone.");
			lua_pushnumber(L, 0);
			return 1;
		}
	}

	int placed = 0;
	for(int dy = -1; dy <= 1; ++dy) {
		for(int dx = -1; dx <= 1; ++dx) {
			if(dx == 0 && dy == 0)
				continue;
			Position p(target->pos.x + dx, target->pos.y + dy, target->pos.z);
			if(placeCrimsonCageWall(spell->game, p)) {
				sendSpellMagicEffect(spell->game, p, NM_ME_MAGIC_BLOOD);
				++placed;
			}
		}
	}

	if(placed == 0) {
		if(caster)
			caster->sendCancel("There is no room for a cage there.");
		sendSpellMagicEffect(spell->game, creature->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	SpectatorVec list;
	spell->game->getSpectators(Range(creature->pos, target->pos), list);
	for(SpectatorVec::iterator it = list.begin(); it != list.end(); ++it) {
		Player* spectator = dynamic_cast<Player*>(*it);
		if(spectator)
			spectator->sendDistanceShoot(creature->pos, target->pos, NM_ANI_FIRE);
	}
	sendSpellMagicEffect(spell->game, target->pos, NM_ME_SOUND_RED);

	if(targetPlayer)
		targetPlayer->sendTextMessage(MSG_SMALLINFO, "You are trapped in a crimson cage.");

	if(caster && targetPlayer && caster->access < g_config.ACCESS_PROTECT &&
		spell->game->getWorldType() != WORLD_TYPE_NO_PVP)
	{
		caster->pzLocked = true;
		caster->inFightTicks = std::max(g_config.PZ_LOCKED, caster->inFightTicks);
		targetPlayer->inFightTicks = std::max(g_config.PZ_LOCKED, targetPlayer->inFightTicks);
		caster->sendIcons();
		targetPlayer->sendIcons();
	}

	applyPlayerSpellExhaust(caster, false);
	lua_pushnumber(L, 1);
	return 1;
}

namespace {

Item* findCorpseOnTile(Tile* tile)
{
	if(!tile)
		return NULL;

	const int thingCount = tile->getThingCount();
	for(int stackpos = 1; stackpos < thingCount; ++stackpos) {
		Item* item = dynamic_cast<Item*>(tile->getThingByStackPos(stackpos));
		if(!item)
			continue;

		const unsigned short itemId = item->getID();
		if(itemId == ITEM_MALE_CORPSE || itemId == ITEM_FEMALE_CORPSE || itemId == ITEM_HUMAN_CORPSE)
			return item;

		if(Item::items[itemId].isContainer() && itemId >= 2800 && itemId <= 3110)
			return item;
	}

	return NULL;
}

void restoreFromParalyzeRune(Game* game, unsigned long creatureId)
{
	if(!game)
		return;

	Creature* creature = game->getCreatureByID(creatureId);
	if(!creature)
		return;

	creature->hasteTicks = 0;
	game->changeSpeed(creatureId, creature->getNormalSpeed());
	creature->getConditions()[ATTACK_PARALYZE].clear();

	Player* player = dynamic_cast<Player*>(creature);
	if(player)
		player->sendIcons();
}

}

int SpellScript::luaActionDoCurePoison(lua_State *L)
{
	Position pos;
	internalGetPosition(L, pos);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* caster = spell->game->getCreatureByID(cid);
	if(!caster) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Player* casterPlayer = dynamic_cast<Player*>(caster);
	if(playerSpellExhaustBlocked(casterPlayer)) {
		lua_pushnumber(L, 0);
		return 1;
	}

	if(caster->pos.z != pos.z) {
		caster->sendCancel("You need to be on the same floor.");
		lua_pushnumber(L, 0);
		return 1;
	}

	if(spell->game->canThrowObjectTo(caster->pos, pos, BLOCK_PROJECTILE) != RET_NOERROR) {
		caster->sendCancel("You cannot throw there.");
		lua_pushnumber(L, 0);
		return 1;
	}

	Tile* tile = spell->game->getTile(pos);
	if(!tile) {
		sendSpellMagicEffect(spell->game, caster->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* target = tile->getTopCreature();
	if(!target)
		target = caster;

	if(!target->getConditions().hasCondition(ATTACK_POISON)) {
		sendSpellMagicEffect(spell->game, caster->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	target->getConditions()[ATTACK_POISON].clear();
	Player* targetPlayer = dynamic_cast<Player*>(target);
	if(targetPlayer)
		targetPlayer->sendIcons();

	sendSpellMagicEffect(spell->game, target->pos, NM_ME_MAGIC_ENERGIE);
	applyPlayerSpellExhaust(casterPlayer, true);
	lua_pushnumber(L, 1);
	return 1;
}

int SpellScript::luaActionDoAnimateDead(lua_State *L)
{
	Position pos;
	internalGetPosition(L, pos);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Player* player = dynamic_cast<Player*>(spell->game->getCreatureByID(cid));
	if(!player) {
		lua_pushnumber(L, 0);
		return 1;
	}

	if(playerSpellExhaustBlocked(player)) {
		lua_pushnumber(L, 0);
		return 1;
	}

	if(player->pos.z != pos.z) {
		player->sendCancel("You need to be on the same floor.");
		lua_pushnumber(L, 0);
		return 1;
	}

	if(spell->game->canThrowObjectTo(player->pos, pos, BLOCK_PROJECTILE) != RET_NOERROR) {
		player->sendCancel("You cannot throw there.");
		lua_pushnumber(L, 0);
		return 1;
	}

	Tile* tile = spell->game->getTile(pos);
	if(!tile || tile->isPz()) {
		sendSpellMagicEffect(spell->game, player->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	Item* corpse = findCorpseOnTile(tile);
	if(!corpse) {
		sendSpellMagicEffect(spell->game, player->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	if(player->getSummonCount() >= g_config.MAX_SUMMONS) {
		player->sendCancel("You cannot have more summons.");
		sendSpellMagicEffect(spell->game, player->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	Monster* skeleton = Monster::createMonster("skeleton", spell->game);
	if(!skeleton) {
		sendSpellMagicEffect(spell->game, player->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	Position spawnPos = pos;
	if(!spell->game->placeCreature(spawnPos, skeleton)) {
		delete skeleton;
		sendSpellMagicEffect(spell->game, player->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	if(!removeTileItem(spell->game, player, corpse)) {
		spell->game->removeCreature(skeleton);
		sendSpellMagicEffect(spell->game, player->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	player->addSummon(skeleton);
	sendSpellMagicEffect(spell->game, spawnPos, NM_ME_MAGIC_ENERGIE);
	applyPlayerSpellExhaust(player, false);
	lua_pushnumber(L, 1);
	return 1;
}

int SpellScript::luaActionDoConvinceCreature(lua_State *L)
{
	Position pos;
	internalGetPosition(L, pos);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Player* player = dynamic_cast<Player*>(spell->game->getCreatureByID(cid));
	if(!player) {
		lua_pushnumber(L, 0);
		return 1;
	}

	if(playerSpellExhaustBlocked(player)) {
		lua_pushnumber(L, 0);
		return 1;
	}

	if(player->pos.z != pos.z) {
		player->sendCancel("You need to be on the same floor.");
		lua_pushnumber(L, 0);
		return 1;
	}

	if(spell->game->canThrowObjectTo(player->pos, pos, BLOCK_PROJECTILE) != RET_NOERROR) {
		player->sendCancel("You cannot throw there.");
		lua_pushnumber(L, 0);
		return 1;
	}

	Tile* tile = spell->game->getTile(pos);
	if(!tile || tile->isPz()) {
		sendSpellMagicEffect(spell->game, player->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	Monster* monster = dynamic_cast<Monster*>(tile->getTopCreature());
	if(!monster || monster->isSummon() || dynamic_cast<Player*>(monster)) {
		sendSpellMagicEffect(spell->game, player->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	if(player->getSummonCount() >= g_config.MAX_SUMMONS) {
		player->sendCancel("You cannot have more summons.");
		sendSpellMagicEffect(spell->game, player->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	int64_t reqMana = (monster->healthmax + monster->manamax) / 4;
	const int64_t summonMana = Summons::getRequiredMana(monster->getName());
	if(summonMana >= 0)
		reqMana = summonMana;

	if(player->access < g_config.ACCESS_PROTECT && player->mana < reqMana) {
		player->sendCancel("Not enough mana.");
		sendSpellMagicEffect(spell->game, player->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	player->addSummon(monster);
	if(player->access < g_config.ACCESS_PROTECT) {
		player->mana -= reqMana;
		player->addManaSpent(reqMana);
	}

	sendSpellMagicEffect(spell->game, monster->pos, NM_ME_MAGIC_ENERGIE);
	applyPlayerSpellExhaust(player, false);
	lua_pushnumber(L, 1);
	return 1;
}

int SpellScript::luaActionDoChameleon(lua_State *L)
{
	const long CHAMELEON_MS = 200000;

	Position pos;
	internalGetPosition(L, pos);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Player* player = dynamic_cast<Player*>(spell->game->getCreatureByID(cid));
	if(!player) {
		lua_pushnumber(L, 0);
		return 1;
	}

	if(playerSpellExhaustBlocked(player)) {
		lua_pushnumber(L, 0);
		return 1;
	}

	if(player->pos.z != pos.z) {
		player->sendCancel("You need to be on the same floor.");
		lua_pushnumber(L, 0);
		return 1;
	}

	if(spell->game->canThrowObjectTo(player->pos, pos, BLOCK_PROJECTILE) != RET_NOERROR) {
		player->sendCancel("You cannot throw there.");
		lua_pushnumber(L, 0);
		return 1;
	}

	Tile* tile = spell->game->getTile(pos);
	if(!tile) {
		sendSpellMagicEffect(spell->game, player->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* target = tile->getTopCreature();
	if(!target) {
		sendSpellMagicEffect(spell->game, player->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	const int savedLookMaster = player->lookmaster;
	player->looktype = target->looktype;
	player->lookhead = target->lookhead;
	player->lookbody = target->lookbody;
	player->looklegs = target->looklegs;
	player->lookfeet = target->lookfeet;
	spell->game->creatureChangeOutfit(player);
	spell->game->changeOutfitAfter(player->getID(), savedLookMaster, CHAMELEON_MS);
	sendSpellMagicEffect(spell->game, player->pos, NM_ME_MAGIC_ENERGIE);
	applyPlayerSpellExhaust(player, true);
	lua_pushnumber(L, 1);
	return 1;
}

int SpellScript::luaActionDoParalyze(lua_State *L)
{
	const long PARALYZE_RUNE_MS = 60000;
	const unsigned short PARALYZE_SPEED = 40;

	Position pos;
	internalGetPosition(L, pos);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* caster = spell->game->getCreatureByID(cid);
	if(!caster) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Player* casterPlayer = dynamic_cast<Player*>(caster);
	if(playerSpellExhaustBlocked(casterPlayer)) {
		lua_pushnumber(L, 0);
		return 1;
	}

	if(caster->pos.z != pos.z) {
		caster->sendCancel("You need to be on the same floor.");
		lua_pushnumber(L, 0);
		return 1;
	}

	if(spell->game->canThrowObjectTo(caster->pos, pos, BLOCK_PROJECTILE) != RET_NOERROR) {
		caster->sendCancel("You cannot throw there.");
		lua_pushnumber(L, 0);
		return 1;
	}

	Tile* tile = spell->game->getTile(pos);
	if(!tile) {
		sendSpellMagicEffect(spell->game, caster->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* target = tile->getTopCreature();
	if(!target || target == caster) {
		sendSpellMagicEffect(spell->game, caster->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	if(target->access >= g_config.ACCESS_PROTECT) {
		sendSpellMagicEffect(spell->game, caster->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	if((target->getImmunities() & ATTACK_PARALYZE) == ATTACK_PARALYZE) {
		sendSpellMagicEffect(spell->game, caster->pos, NM_ME_PUFF);
		lua_pushnumber(L, 0);
		return 1;
	}

	Player* targetPlayer = dynamic_cast<Player*>(target);
	if(casterPlayer && casterPlayer->access < g_config.ACCESS_PROTECT) {
		Tile* fromTile = spell->game->getTile(caster->pos);
		if(fromTile && fromTile->isPz()) {
			casterPlayer->sendTextMessage(MSG_SMALLINFO, "You may not attack a person while you are in a protection zone.");
			lua_pushnumber(L, 0);
			return 1;
		}
		if(tile->isPz()) {
			casterPlayer->sendTextMessage(MSG_SMALLINFO, "You may not attack a person in a protection zone.");
			lua_pushnumber(L, 0);
			return 1;
		}
	}

	target->hasteTicks = 0;
	spell->game->changeSpeed(target->getID(), PARALYZE_SPEED);

	MagicEffectTargetCreatureCondition paralyzeCond(caster ? caster->getID() : 0);
	paralyzeCond.attackType = ATTACK_PARALYZE;
	CreatureCondition condition(1000, PARALYZE_RUNE_MS / 1000, paralyzeCond);
	target->addCondition(condition, true);
	target->hasteTicks = PARALYZE_RUNE_MS;

	if(targetPlayer)
		targetPlayer->sendIcons();

	if(casterPlayer && targetPlayer && casterPlayer->access < g_config.ACCESS_PROTECT &&
		spell->game->getWorldType() != WORLD_TYPE_NO_PVP)
	{
		casterPlayer->pzLocked = true;
		casterPlayer->inFightTicks = std::max(g_config.PZ_LOCKED, casterPlayer->inFightTicks);
		targetPlayer->inFightTicks = std::max(g_config.PZ_LOCKED, targetPlayer->inFightTicks);
		casterPlayer->sendIcons();
	}

	sendSpellMagicEffect(spell->game, target->pos, NM_ME_MAGIC_ENERGIE);
	spell->game->addEvent(makeTask(PARALYZE_RUNE_MS,
		boost::bind(&restoreFromParalyzeRune, spell->game, target->getID())));

	applyPlayerSpellExhaust(casterPlayer, false);
	lua_pushnumber(L, 1);
	return 1;
}

// doChallenge(cid) — Challenge / exeta res: nearby monsters target caster for 6s.
int SpellScript::luaActionDoChallenge(lua_State *L)
{
	const long CHALLENGE_MS = 6000;
	const int RANGE = 1; // Chebyshev: 3×3 around caster (classic "nearby")

	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* caster = spell->game->getCreatureByID(cid);
	if(!caster) {
		lua_pushnumber(L, 0);
		return 1;
	}

	int affected = 0;
	for(int dy = -RANGE; dy <= RANGE; ++dy) {
		for(int dx = -RANGE; dx <= RANGE; ++dx) {
			Position p(caster->pos.x + dx, caster->pos.y + dy, caster->pos.z);
			Tile* tile = spell->game->getTile(p);
			if(!tile)
				continue;

			// Copy ids first — applyChallenge may mutate think state.
			std::vector<unsigned long> ids;
			for(CreatureVector::const_iterator it = tile->creatures.begin();
				it != tile->creatures.end(); ++it) {
				if(*it)
					ids.push_back((*it)->getID());
			}

			for(std::vector<unsigned long>::const_iterator idIt = ids.begin();
				idIt != ids.end(); ++idIt) {
				Creature* c = spell->game->getCreatureByID(*idIt);
				if(!c || c == caster)
					continue;

				Monster* monster = dynamic_cast<Monster*>(c);
				if(!monster || monster->isSummon())
					continue;

				monster->applyChallenge(caster, CHALLENGE_MS);
				sendSpellMagicEffect(spell->game, monster->pos, NM_ME_MAGIC_ENERGIE);
				++affected;
			}
		}
	}

	sendSpellMagicEffect(spell->game, caster->pos, NM_ME_SOUND_BLUE);
	(void)affected;
	lua_pushnumber(L, 1); // success even with no monsters nearby (mana already spent via doTargetMagic)
	return 1;
}

// ---------- Cooldowns propios por hechizo ----------

int SpellScript::luaActionSpellCooldownReady(lua_State *L)
{
	const char* name = lua_tostring(L, -1);
	unsigned int cid = (unsigned int)lua_tonumber(L, -2);
	lua_pop(L, 2);

	if(!name)
	{
		lua_pushnumber(L, 0);
		return 1;
	}

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* creature = spell->game->getCreatureByID(cid);
	if(!creature) {
		lua_pushnumber(L, 0);
		return 1;
	}

	int left = PlayerSpellCooldown::remaining(creature->getID(), std::string(name));
	if(left > 0) {
		Player* player = dynamic_cast<Player*>(creature);
		if(player) {
			std::stringstream msg;
			msg << "You can use it again in " << spellSeconds(left) << " s.";
			spellFail(spell->game, player, msg.str());
		}
	}
	lua_pushnumber(L, left);
	return 1;
}

int SpellScript::luaActionSetSpellCooldown(lua_State *L)
{
	int ms = (int)lua_tonumber(L, -1);
	const char* name = lua_tostring(L, -2);
	unsigned int cid = (unsigned int)lua_tonumber(L, -3);
	lua_pop(L, 3);

	if(!name)
		return 0;

	Spell* spell = getSpell(L);
	if(!spell)
		return 0;

	Creature* creature = spell->game->getCreatureByID(cid);
	if(!creature)
		return 0;

	PlayerSpellCooldown::set(creature->getID(), std::string(name), ms);
	// El cliente deja el ícono del hechizo (apagado, con la cuenta) hasta que se pueda volver a usar.
	// Texto exacto en TimedIcons de clienteretro: "<nombre del hechizo>: ready again in N s."
	if(ms > 0) {
		std::stringstream msg;
		msg << spellTitle(spell->getName()) << ": ready again in " << spellSeconds(ms) << " s.";
		sendSpellText(creature, MSG_SMALLINFO, msg.str());
	}
	return 0;
}

// ---------- Nuevos spells ----------

// Helper: lee un nombre de criatura del stack y lo busca.
static Creature* readNamedCreature(lua_State* L, Spell* spell, std::string& outName)
{
	const char* s = lua_tostring(L, -1);
	if(!s)
		return NULL;
	outName = std::string(s);
	lua_pop(L, 1);
	return spell->game->getCreatureByName(outName);
}

int SpellScript::luaActionDoRescue(lua_State *L)
{
	long durationMs = (long)lua_tonumber(L, -1) * 1000;
	lua_pop(L, 1);
	int radius = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	std::string targetName;
	Creature* named = readNamedCreature(L, getSpell(L), targetName);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* caster = spell->game->getCreatureByID(cid);
	Player* casterPlayer = dynamic_cast<Player*>(caster);
	if(!caster || !casterPlayer) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Player* ally = dynamic_cast<Player*>(named);
	if(!ally || ally == casterPlayer) {
		spellFail(spell->game, caster, "You cannot rescue that target.");
		lua_pushnumber(L, 0);
		return 1;
	}

	if(caster->pos.z != ally->pos.z) {
		spellFail(spell->game, caster, "You need to be on the same floor.");
		lua_pushnumber(L, 0);
		return 1;
	}

	int affected = 0;
	for(int dy = -radius; dy <= radius; ++dy) {
		for(int dx = -radius; dx <= radius; ++dx) {
			Position p(ally->pos.x + dx, ally->pos.y + dy, ally->pos.z);
			Tile* tile = spell->game->getTile(p);
			if(!tile)
				continue;

			std::vector<unsigned long> ids;
			for(CreatureVector::const_iterator it = tile->creatures.begin();
				it != tile->creatures.end(); ++it) {
				if(*it)
					ids.push_back((*it)->getID());
			}

			for(std::vector<unsigned long>::const_iterator idIt = ids.begin();
				idIt != ids.end(); ++idIt) {
				Creature* c = spell->game->getCreatureByID(*idIt);
				if(!c || c == caster || c == ally)
					continue;

				Monster* monster = dynamic_cast<Monster*>(c);
				if(!monster || monster->isSummon())
					continue;

				// Solo los que realmente atacan al aliado.
				if(monster->attackedCreature != ally->getID())
					continue;

				monster->applyChallenge(caster, durationMs);
				sendSpellMagicEffect(spell->game, monster->pos, NM_ME_SOUND_BLUE);
				++affected;
			}
		}
	}

	if(affected > 0) {
		sendSpellMagicEffect(spell->game, ally->pos, NM_ME_RALLY_RING);
		std::stringstream msg;
		msg << "You draw " << affected << (affected == 1 ? " monster" : " monsters") << " away from "
			<< ally->getName() << " for " << spellSeconds(durationMs) << " s.";
		sendSpellText(caster, MSG_INFO, msg.str());
		sendSpellText(ally, MSG_INFO, caster->getName() + " draws the monsters away from you.");
		spell->game->addEvent(makeTask(durationMs,
			boost::bind(&sendSpellTextLater, spell->game, caster->getID(), std::string("Your rescue ends."))));
	}
	else {
		spellFail(spell->game, caster, ("No monsters are attacking " + ally->getName() + ".").c_str());
	}

	lua_pushnumber(L, affected);
	return 1;
}

int SpellScript::luaActionDoCleanse(lua_State *L)
{
	std::string targetName;
	Creature* named = readNamedCreature(L, getSpell(L), targetName);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* caster = spell->game->getCreatureByID(cid);
	if(!caster) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Player* target = dynamic_cast<Player*>(named);
	if(!target) {
		spellFail(spell->game, caster, "You cannot cleanse that target.");
		lua_pushnumber(L, 0);
		return 1;
	}

	if(caster->pos.z != target->pos.z) {
		spellFail(spell->game, caster, "You need to be on the same floor.");
		lua_pushnumber(L, 0);
		return 1;
	}

	bool hadPoison = target->getConditions().hasCondition(ATTACK_POISON);
	bool hadParalyze = target->getConditions().hasCondition(ATTACK_PARALYZE);

	if(!hadPoison && !hadParalyze) {
		spellFail(spell->game, caster, "The target has no ailments to cleanse.");
		lua_pushnumber(L, 0);
		return 1;
	}

	if(hadPoison)
		target->getConditions()[ATTACK_POISON].clear();

	if(hadParalyze) {
		target->getConditions()[ATTACK_PARALYZE].clear();
		target->hasteTicks = 0;
		spell->game->changeSpeed(target->getID(), target->getNormalSpeed());
	}

	target->sendIcons();
	target->sendStats();
	sendSpellMagicEffect(spell->game, target->pos, NM_ME_CLEANSE_SWIRL);

	std::string removed = hadPoison && hadParalyze ? "poison and paralysis" : (hadPoison ? "poison" : "paralysis");
	if(target == caster) {
		sendSpellText(caster, MSG_INFO, "You cleanse yourself: " + removed + " removed.");
	}
	else {
		sendSpellText(caster, MSG_INFO, "You cleanse " + target->getName() + ": " + removed + " removed.");
		sendSpellText(target, MSG_INFO, caster->getName() + " cleanses you: " + removed + " removed.");
	}
	lua_pushnumber(L, 1);
	return 1;
}

int SpellScript::luaActionDoChainLightning(lua_State *L)
{
	int maxDmg = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int minDmg = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int falloff = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int range = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int jumps = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	Position targetPos;
	internalGetPosition(L, targetPos);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* caster = spell->game->getCreatureByID(cid);
	Player* casterPlayer = dynamic_cast<Player*>(caster);
	if(!caster || !casterPlayer) {
		lua_pushnumber(L, 0);
		return 1;
	}

	if(caster->pos.z != targetPos.z) {
		spellFail(spell->game, caster, "You need to be on the same floor.");
		lua_pushnumber(L, 0);
		return 1;
	}

	if(spell->game->canThrowObjectTo(caster->pos, targetPos, BLOCK_PROJECTILE) != RET_NOERROR) {
		spellFail(spell->game, caster, "You cannot throw there.");
		lua_pushnumber(L, 0);
		return 1;
	}

	Tile* startTile = spell->game->getTile(targetPos);
	if(!startTile) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* start = startTile->getTopCreature();
	Monster* first = dynamic_cast<Monster*>(start);
	if(!first) {
		spellFail(spell->game, caster, "You can only chain lightning through monsters.");
		lua_pushnumber(L, 0);
		return 1;
	}

	std::set<unsigned long> visited;
	std::vector<Creature*> chain;
	chain.push_back(first);
	visited.insert(first->getID());

	Creature* current = first;
	for(int i = 0; i < jumps && current; ++i) {
		Creature* next = NULL;
		int bestDist = range + 1;
		for(int dy = -range; dy <= range; ++dy) {
			for(int dx = -range; dx <= range; ++dx) {
				Position p(current->pos.x + dx, current->pos.y + dy, current->pos.z);
				Tile* tile = spell->game->getTile(p);
				if(!tile)
					continue;
				Creature* c = tile->getTopCreature();
				if(!c || c == caster)
					continue;
				if(visited.find(c->getID()) != visited.end())
					continue;
				Monster* m = dynamic_cast<Monster*>(c);
				if(!m)
					continue;
				int dist = std::max(std::abs(dx), std::abs(dy));
				if(dist < bestDist && spell->game->canThrowObjectTo(current->pos, p, BLOCK_PROJECTILE) == RET_NOERROR) {
					bestDist = dist;
					next = c;
				}
			}
		}
		if(!next)
			break;
		current = next;
		chain.push_back(current);
		visited.insert(current->getID());
	}

	int applied = 0;
	int factor = 100;
	for(size_t i = 0; i < chain.size(); ++i) {
		Creature* target = chain[i];
		if((target->getImmunities() & ATTACK_ENERGY) == ATTACK_ENERGY)
			continue;

		int dmgMin = minDmg * factor / 100;
		int dmgMax = maxDmg * factor / 100;
		if(dmgMax < 1)
			dmgMax = 1;
		if(dmgMin > dmgMax)
			dmgMin = dmgMax;

		int64_t dmg = dmgMin;
		if(dmgMax > dmgMin)
			dmg += rand() % (dmgMax - dmgMin + 1);

		int64_t outDamage = 0, outMana = 0;
		spell->game->creatureApplyDamage(target, dmg, outDamage, outMana, NULL);
		if(outDamage > 0) {
			sendSpellMagicEffect(spell->game, target->pos, NM_ME_CHAIN_ARC);
			Player* p = dynamic_cast<Player*>(target);
			if(p)
				p->sendStats();
			++applied;
		}
		factor = factor * falloff / 100;
	}

	if(applied > 0) {
		casterPlayer->pzLocked = true;
		std::stringstream msg;
		if(applied == 1)
			msg << "Your lightning strikes 1 monster.";
		else
			msg << "Your lightning chains through " << applied << " monsters.";
		sendSpellText(caster, MSG_INFO, msg.str());
	}
	else {
		spellFail(spell->game, caster, "The lightning has no effect.");
	}

	lua_pushnumber(L, applied);
	return 1;
}

namespace {

struct DelayedHealJob {
	unsigned long casterId;
	unsigned long targetId;
	int minHeal;
	int maxHeal;
	int range;
};

void runDelayedHeal(Game* game, const DelayedHealJob& job)
{
	Creature* target = game->getCreatureByID(job.targetId);
	Creature* caster = game->getCreatureByID(job.casterId);
	if(!target)
		return;
	// El cliente apaga el ícono de la semilla con cualquiera de los dos textos.
	if(!caster || target->pos.z != caster->pos.z ||
	   std::max(std::abs((int)target->pos.x - (int)caster->pos.x),
	            std::abs((int)target->pos.y - (int)caster->pos.y)) > job.range) {
		sendSpellText(target, MSG_SMALLINFO, "The seed of life withers.");
		return;
	}

	int64_t heal = job.minHeal;
	if(job.maxHeal > job.minHeal)
		heal += rand() % (job.maxHeal - job.minHeal + 1);

	int64_t newHealth = target->health + heal;
	if(newHealth > target->healthmax)
		newHealth = target->healthmax;
	target->health = newHealth;

	sendSpellMagicEffect(game, target->pos, NM_ME_SEED_BURST);
	if(Player* p = dynamic_cast<Player*>(target))
		p->sendStats();
	sendSpellText(target, MSG_SMALLINFO, "The seed of life blooms.");
}

} // namespace

int SpellScript::luaActionDoDelayedHeal(lua_State *L)
{
	int range = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int delayedMax = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int delayedMin = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	long delayMs = (long)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int immediateMax = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int immediateMin = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	std::string targetName;
	Creature* named = readNamedCreature(L, getSpell(L), targetName);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* caster = spell->game->getCreatureByID(cid);
	if(!caster) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Player* target = dynamic_cast<Player*>(named);
	if(!target) {
		spellFail(spell->game, caster, "You can only heal players.");
		lua_pushnumber(L, 0);
		return 1;
	}

	if(caster->pos.z != target->pos.z) {
		spellFail(spell->game, caster, "You need to be on the same floor.");
		lua_pushnumber(L, 0);
		return 1;
	}

	// Curación inmediata.
	int64_t immediate = immediateMin;
	if(immediateMax > immediateMin)
		immediate += rand() % (immediateMax - immediateMin + 1);
	int64_t newHealth = target->health + immediate;
	if(newHealth > target->healthmax)
		newHealth = target->healthmax;
	target->health = newHealth;
	target->sendStats();
	sendSpellMagicEffect(spell->game, target->pos, NM_ME_SEED_BURST);

	// Curación diferida.
	DelayedHealJob job;
	job.casterId = caster->getID();
	job.targetId = target->getID();
	job.minHeal = delayedMin;
	job.maxHeal = delayedMax;
	job.range = range;

	spell->game->addEvent(makeTask(delayMs,
		boost::bind(&runDelayedHeal, spell->game, job)));

	std::stringstream msg;
	msg << "A seed of life will bloom on you in " << spellSeconds(delayMs) << " s.";
	sendSpellText(target, MSG_INFO, msg.str());
	if(target != caster)
		sendSpellText(caster, MSG_INFO, "You plant a seed of life on " + target->getName() + ".");

	lua_pushnumber(L, 1);
	return 1;
}

int SpellScript::luaActionDoDetonateFields(lua_State *L)
{
	int maxDmg = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int minDmg = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int maxFields = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int radius = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	Position center;
	internalGetPosition(L, center);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* caster = spell->game->getCreatureByID(cid);
	Player* casterPlayer = dynamic_cast<Player*>(caster);
	if(!caster || !casterPlayer) {
		lua_pushnumber(L, 0);
		return 1;
	}

	if(caster->pos.z != center.z) {
		spellFail(spell->game, caster, "You need to be on the same floor.");
		lua_pushnumber(L, 0);
		return 1;
	}

	if(spell->game->canThrowObjectTo(caster->pos, center, BLOCK_PROJECTILE) != RET_NOERROR) {
		spellFail(spell->game, caster, "You cannot throw there.");
		lua_pushnumber(L, 0);
		return 1;
	}

	int detonated = 0;
	for(int dy = -radius; detonated < maxFields && dy <= radius; ++dy) {
		for(int dx = -radius; detonated < maxFields && dx <= radius; ++dx) {
			Position p(center.x + dx, center.y + dy, center.z);
			Tile* tile = spell->game->getTile(p);
			if(!tile)
				continue;

			MagicEffectItem* field = tile->getFieldItem();
			if(!field)
				continue;

			// Solo fuego, energía o veneno; no magic wall ni wild growth.
			attacktype_t fieldType = field->attackType;
			if(fieldType != ATTACK_FIRE && fieldType != ATTACK_ENERGY && fieldType != ATTACK_POISON)
				continue;

			if(!removeTileItem(spell->game, caster, field))
				continue;

			++detonated;

			unsigned char effect = NM_ME_FIRE_AREA;
			if(fieldType == ATTACK_ENERGY)
				effect = NM_ME_ENERGY_AREA;
			else if(fieldType == ATTACK_POISON)
				effect = NM_ME_POISEN;
			sendSpellMagicEffect(spell->game, p, effect);

			Creature* victim = tile->getTopCreature();
			if(!victim || (victim->getImmunities() & fieldType) == fieldType)
				continue;

			int64_t dmg = minDmg;
			if(maxDmg > minDmg)
				dmg += rand() % (maxDmg - minDmg + 1);

			int64_t outDamage = 0, outMana = 0;
			spell->game->creatureApplyDamage(victim, dmg, outDamage, outMana, NULL);
			if(outDamage > 0) {
				Player* p = dynamic_cast<Player*>(victim);
				if(p)
					p->sendStats();
			}
		}
	}

	if(detonated > 0) {
		casterPlayer->pzLocked = true;
		std::stringstream msg;
		msg << "You detonate " << detonated << (detonated == 1 ? " field." : " fields.");
		sendSpellText(caster, MSG_INFO, msg.str());
	}
	else {
		spellFail(spell->game, caster, "There are no fire, energy or poison fields around you.");
	}

	lua_pushnumber(L, detonated);
	return 1;
}

int SpellScript::luaActionDoCounterStance(lua_State *L)
{
	int reduction = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int hits = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	long durationMs = (long)lua_tonumber(L, -1) * 1000;
	lua_pop(L, 1);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* caster = spell->game->getCreatureByID(cid);
	Player* player = dynamic_cast<Player*>(caster);
	if(!player) {
		lua_pushnumber(L, 0);
		return 1;
	}

	CounterStanceState state;
	state.hits = hits;
	state.reduction = reduction;
	state.until = OTSYS_TIME() + durationMs;
	g_counterStance[player->getID()] = state;
	spell->game->addEvent(makeTask(durationMs,
		boost::bind(&endCounterStance, spell->game, player->getID(), state.until)));

	sendSpellMagicEffect(spell->game, player->pos, NM_ME_STANCE_GUARD);
	std::stringstream msg;
	msg << "You take a counter stance for " << spellSeconds(durationMs) << " s: the next " << hits
		<< (hits == 1 ? " hit deals " : " hits deal ") << reduction << "% less damage.";
	sendSpellText(player, MSG_INFO, msg.str());
	lua_pushnumber(L, 1);
	return 1;
}

namespace {

struct BloodRitualState {
	unsigned long playerId;
	int ticksLeft;
	int tickMs;
	int hpPerTick;
	int manaPerTick;
	int minHpPercent;
};

void runBloodRitualTick(Game* game, BloodRitualState state)
{
	Creature* creature = game->getCreatureByID(state.playerId);
	if(!creature)
		return;
	Player* player = dynamic_cast<Player*>(creature);
	if(!player)
		return;

	// El cliente apaga el ícono con "Your blood ritual ends."
	Tile* tile = game->getTile(player->pos);
	if(tile && tile->isPz()) {
		player->sendTextMessage(MSG_SMALLINFO, "Your blood ritual ends.");
		return;
	}

	int64_t minHp = player->healthmax * state.minHpPercent / 100;
	int64_t drain = state.hpPerTick;
	if(player->health - drain < minHp)
		drain = player->health - minHp;
	if(drain <= 0) {
		player->sendTextMessage(MSG_SMALLINFO, "Your blood ritual ends.");
		return;
	}

	player->health -= drain;
	player->mana = std::min(player->manamax, player->mana + (int64_t)state.manaPerTick);
	player->sendStats();
	sendSpellMagicEffect(game, player->pos, NM_ME_BLOOD_SPIRAL);

	if(--state.ticksLeft > 0) {
		game->addEvent(makeTask(state.tickMs,
			boost::bind(&runBloodRitualTick, game, state)));
	}
	else {
		player->sendTextMessage(MSG_SMALLINFO, "Your blood ritual ends.");
	}
}

} // namespace

int SpellScript::luaActionDoBloodRitual(lua_State *L)
{
	int minHpPercent = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int manaPerTick = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int hpPerTick = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int tickMs = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int totalTicks = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	if(!spell) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Creature* caster = spell->game->getCreatureByID(cid);
	Player* player = dynamic_cast<Player*>(caster);
	if(!player) {
		lua_pushnumber(L, 0);
		return 1;
	}

	Tile* tile = spell->game->getTile(player->pos);
	if(tile && tile->isPz()) {
		spellFail(spell->game, player, "You cannot use this spell in a protection zone.");
		lua_pushnumber(L, 0);
		return 1;
	}

	int64_t minHp = player->healthmax * minHpPercent / 100;
	if(player->health <= minHp) {
		spellFail(spell->game, player, "Your health is too low.");
		lua_pushnumber(L, 0);
		return 1;
	}

	BloodRitualState state;
	state.playerId = player->getID();
	state.ticksLeft = totalTicks;
	state.tickMs = tickMs;
	state.hpPerTick = hpPerTick;
	state.manaPerTick = manaPerTick;
	state.minHpPercent = minHpPercent;

	spell->game->addEvent(makeTask(tickMs,
		boost::bind(&runBloodRitualTick, spell->game, state)));

	sendSpellMagicEffect(spell->game, player->pos, NM_ME_BLOOD_SPIRAL);
	std::stringstream msg;
	msg << "Your blood turns into mana for " << spellSeconds((long)totalTicks * tickMs) << " s: "
		<< hpPerTick << " health into " << manaPerTick << " mana every " << spellSeconds(tickMs) << " s.";
	player->sendTextMessage(MSG_INFO, msg.str().c_str());
	lua_pushnumber(L, 1);
	return 1;
}

Spell* SpellScript::getSpell(lua_State *L) {
	lua_getglobal(L, "addressOfSpell");
	Spell* myspell = (Spell*)lua_touserdata(L, -1);
	lua_pop(L,1);

	if(!myspell){
		return 0;
	}
	return myspell;
}

void SpellScript::internalGetArea(lua_State *L, MagicEffectAreaClass &magicArea)
{
	std::vector<unsigned char> col;

	int i=0, j = 0;
	lua_pushnil(L);  /* first key */

	while (lua_next(L, -2) != 0) {
		lua_pushnil(L);
		col.clear();
    while (lua_next(L, -2) != 0) {
			col.push_back((unsigned char)lua_tonumber(L, -1));

			lua_pop(L, 1);  /* removes `value'; keeps `key' for next iteration */
			j++;
		}

		magicArea.areaVec.push_back(col);

		j=0;
		lua_pop(L, 1);  /* removes `value'; keeps `key' for next iteration */
		i++;
	}

	lua_pop(L, 1);

	magicArea.areaEffect = (char)lua_tonumber(L, -1);
	lua_pop(L,1);
}

void SpellScript::internalGetPosition(lua_State *L, Position& pos)
{
	lua_pushstring(L, "z");
	lua_gettable(L, -2);
	pos.z = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	lua_pushstring(L, "y");
	lua_gettable(L, -2);
	pos.y = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	lua_pushstring(L, "x");
	lua_gettable(L, -2);
	pos.x = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);

  lua_pop(L, 1); //table
}

void SpellScript::internalGetMagicEffect(lua_State *L, MagicEffectClass& me)
{
	lua_pushnil(L);

	lua_next(L, -2);
	int attackType = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	switch(attackType) {
		case 0: me.attackType = ATTACK_NONE; break;
		case 1: me.attackType = ATTACK_ENERGY; break;
		case 2: me.attackType = ATTACK_BURST; break;
		case 3: me.attackType = ATTACK_FIRE; break;
		case 4: me.attackType = ATTACK_PHYSICAL; break;
		case 5: me.attackType = ATTACK_POISON; break;
		case 6: me.attackType = ATTACK_PARALYZE; break;
		case 7: me.attackType = ATTACK_DRUNKNESS; break;
		case 8: me.attackType = ATTACK_LIFEDRAIN; break;
		case 9: me.attackType = ATTACK_MANADRAIN; break;

		default:
#ifdef __DEBUG__
			std::cerr << "WARNING: internalGetMagicEffect(), attackType out of range!" << std::endl;
#endif
			break;
	}

	lua_next(L, -2);
	me.animationEffect = (char)lua_tonumber(L, -1);
	lua_pop(L, 1);

	lua_next(L, -2);
	me.hitEffect = (char)lua_tonumber(L, -1);
	lua_pop(L, 1);

 	lua_next(L, -2);
	me.damageEffect = (char)lua_tonumber(L, -1);
	lua_pop(L, 1);

	lua_next(L, -2);
	me.animationColor = (char)lua_tonumber(L, -1);
	lua_pop(L, 1);

	lua_next(L, -2);
	me.offensive = (bool)(lua_toboolean(L, -1) > 0);
	lua_pop(L, 1);

	lua_next(L, -2);
	me.drawblood = (bool)(lua_toboolean(L, -1) > 0);
	lua_pop(L, 1);

	lua_next(L, -2);
	me.minDamage = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	lua_next(L, -2);
	me.maxDamage = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	lua_pop(L, 1); // last key

	lua_pop(L, 1); //end of table
}

int SpellScript::luaActionDoTargetSpell(lua_State *L)
{
	MagicEffectTargetClass magicTarget;

	internalGetMagicEffect(L, magicTarget);

	Position centerpos;
	internalGetPosition(L, centerpos);

	Spell* spell = getSpell(L);
	magicTarget.manaCost = spell->getMana();
	if(echoCast) {
		magicTarget.manaCost = 0;
		magicTarget.minDamage = (int)(magicTarget.minDamage * echoScale);
		magicTarget.maxDamage = (int)(magicTarget.maxDamage * echoScale);
	}

	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
  	lua_pop(L,1);
	if(!creature){
		lua_pushboolean(L, false);
		return 1;
	}
	bool isSuccess = spell->game->creatureThrowRune(creature, centerpos, magicTarget);
	lua_pushboolean(L, isSuccess);
	return 1;
}

int SpellScript::luaActionDoTargetExSpell(lua_State *L)
{
	ConditionVec condvec;
	internalLoadDamageVec(L, condvec);

	MagicEffectTargetExClass magicTargetEx(/*md,*/ condvec);

	internalGetMagicEffect(L, magicTargetEx);

	Position centerpos;
	internalGetPosition(L, centerpos);

	Spell* spell = getSpell(L);
  magicTargetEx.manaCost = spell->getMana();

	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
  lua_pop(L,1);
	if(!creature){
		lua_pushboolean(L, false);
		return 1;
	}
	bool isSuccess = spell->game->creatureThrowRune(creature, centerpos, magicTargetEx);
	lua_pushboolean(L, isSuccess);
	return 1;
}

int SpellScript::luaActionDoTargetGroundSpell(lua_State *L)
{
	TransformMap transformMap;
	internalLoadTransformVec(L, transformMap);

	MagicEffectItem* fieldItem = new MagicEffectItem(transformMap);
	MagicEffectTargetGroundClass magicGround(fieldItem);

	magicGround.offensive = (bool)(lua_toboolean(L, -1) > 0);
	lua_pop(L,1);

	magicGround.animationEffect = (char)lua_tonumber(L, -1);
	lua_pop(L,1);

	Position centerpos;
	internalGetPosition(L, centerpos);

	Spell* spell = getSpell(L);
 	magicGround.manaCost = spell->getMana();

	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	if(!creature){
		lua_pushboolean(L, false);
		return 1;
	}
	bool isSuccess = spell->game->creatureThrowRune(creature, centerpos, magicGround);
	lua_pushboolean(L, isSuccess);
	return 1;
}

int SpellScript::luaActionDoAreaSpell(lua_State *L)
{
	MagicEffectAreaClass magicArea;
	internalGetMagicEffect(L, magicArea);

	internalGetArea(L, magicArea);

	bool needDirection = (bool)(lua_toboolean(L, -1) > 0);
	lua_pop(L,1);

	Position centerpos;
	internalGetPosition(L, centerpos);

	Spell* spell = getSpell(L);
  magicArea.manaCost = spell->getMana();
	if(echoCast) {
		magicArea.manaCost = 0;
		magicArea.minDamage = (int)(magicArea.minDamage * echoScale);
		magicArea.maxDamage = (int)(magicArea.maxDamage * echoScale);
	}

	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L,1);
	if(!creature){
		lua_pushboolean(L, false);
		return 1;
	}

	if(needDirection){
		switch(creature->getDirection()) {
			case NORTH: magicArea.direction = 1; break;
			case WEST: magicArea.direction = 2; break;
			case EAST: magicArea.direction = 3; break;
			case SOUTH: magicArea.direction = 4; break;
		};
	}
  else {
		magicArea.direction = 1;
	}
    RuneSpell* runeSpell = dynamic_cast<RuneSpell*>(spell);
    bool isSuccess;
    if(runeSpell)
        isSuccess = spell->game->creatureThrowRune(creature, centerpos, magicArea);
    else
        isSuccess = spell->game->creatureCastSpell(creature, centerpos, magicArea);
    lua_pushboolean(L, isSuccess);
    return 1;
}
int SpellScript::luaActionDoAreaAnimation(lua_State *L)
{
	MagicEffectAreaClass magicArea;
	internalGetMagicEffect(L, magicArea);

	internalGetArea(L, magicArea);

	bool needDirection = (bool)(lua_toboolean(L, -1) > 0);
	lua_pop(L,1);

	Position centerpos;
	internalGetPosition(L, centerpos);

	Spell* spell = getSpell(L);
  magicArea.manaCost = spell->getMana();
	if(echoCast) {
		magicArea.manaCost = 0;
		magicArea.minDamage = (int)(magicArea.minDamage * echoScale);
		magicArea.maxDamage = (int)(magicArea.maxDamage * echoScale);
	}

	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L,1);
	if(!creature){
		lua_pushboolean(L, false);
		return 1;
	}

	if(needDirection){
		switch(creature->getDirection()) {
			case NORTH: magicArea.direction = 1; break;
			case WEST: magicArea.direction = 2; break;
			case EAST: magicArea.direction = 3; break;
			case SOUTH: magicArea.direction = 4; break;
		};
	}
  else {
		magicArea.direction = 1;
	}
    RuneSpell* runeSpell = dynamic_cast<RuneSpell*>(spell);
    bool isSuccess;
    if(runeSpell)
        isSuccess = spell->game->creatureThrowRune(creature, centerpos, magicArea);
    else
        isSuccess = spell->game->creatureCastSpell(creature, centerpos, magicArea);
    lua_pushboolean(L, isSuccess);
    return 1;
}

int SpellScript::luaActionDoAreaExSpell(lua_State *L)
{
	ConditionVec condvec;

	int count = (int)lua_tonumber(L, -1);
	lua_pop(L,1);

	for(int n = 0; n < count; ++n) {
		internalLoadDamageVec(L, condvec);
	}

	MagicEffectAreaExClass magicAreaEx(/*md,*/ condvec);

	internalGetMagicEffect(L, magicAreaEx);

	internalGetArea(L, magicAreaEx);

	bool needDirection = (bool)(lua_toboolean(L, -1) > 0);
	lua_pop(L,1);

	Position centerpos;
	internalGetPosition(L, centerpos);

	Spell* spell = getSpell(L);
  magicAreaEx.manaCost = spell->getMana();

	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L,1);
	if(!creature){
		lua_pushboolean(L, false);
		return 1;
	}

	if(needDirection){
		switch(creature->getDirection()) {
			case NORTH: magicAreaEx.direction = 1; break;
			case WEST: magicAreaEx.direction = 2; break;
			case EAST: magicAreaEx.direction = 3; break;
			case SOUTH: magicAreaEx.direction = 4; break;
		};
	}
  else {
		magicAreaEx.direction = 1;
	}

    RuneSpell* runeSpell = dynamic_cast<RuneSpell*>(spell);
    bool isSuccess;
    if(runeSpell)
        isSuccess = spell->game->creatureThrowRune(creature, centerpos, magicAreaEx);
    else
        isSuccess = spell->game->creatureCastSpell(creature, centerpos, magicAreaEx);

    lua_pushboolean(L, isSuccess);
    return 1;
}

int SpellScript::luaActionDoAreaGroundSpell(lua_State *L)
{
	TransformMap transformMap;
	internalLoadTransformVec(L, transformMap);

	MagicEffectItem* fieldItem = new MagicEffectItem(/*md,*/ transformMap);
	MagicEffectAreaGroundClass magicGroundEx(fieldItem);

	internalGetMagicEffect(L, magicGroundEx);

	internalGetArea(L, magicGroundEx);

	bool needDirection = (bool)(lua_toboolean(L, -1) > 0);
	lua_pop(L,1);

	Position centerpos;
	internalGetPosition(L, centerpos);

	Spell* spell = getSpell(L);
  magicGroundEx.manaCost = spell->getMana();

	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L, 1);
	if(!creature){
		lua_pushboolean(L, false);
		return 1;
	}

	if(needDirection){
		switch(creature->getDirection()) {
			case NORTH: magicGroundEx.direction = 1; break;
			case WEST: magicGroundEx.direction = 2; break;
			case EAST: magicGroundEx.direction = 3; break;
			case SOUTH: magicGroundEx.direction = 4; break;
		};
	}
  else {
		magicGroundEx.direction = 1;
	}

	bool isSuccess = spell->game->creatureThrowRune(creature, centerpos, magicGroundEx);
	lua_pushboolean(L, isSuccess);
	return 1;
}

int SpellScript::luaActionChangeOutfit(lua_State *L){
    int looktype = (int)lua_tonumber(L, -1);
	lua_pop(L,1);
	long time = (long)lua_tonumber(L, -1)*1000;
	lua_pop(L,1);

	Spell* spell = getSpell(L);
	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L,1);

	creature->looktype = looktype;
	spell->game->creatureChangeOutfit(creature);

  spell->game->changeOutfitAfter(creature->getID(), creature->lookmaster, time);
	return 0;
}

void SpellScript::internalLoadDamageVec(lua_State *L, ConditionVec& condvec)
{
	//cid
	unsigned long cid = (int)lua_tonumber(L, 1);

	MagicEffectTargetCreatureCondition magicTargetCondition(cid);

	internalGetMagicEffect(L, magicTargetCondition);

	//conditionTimeCount
	long condCount = (int)lua_tonumber(L, -1); //conditionCount
	lua_pop(L, 1);

	long ticks = (int)lua_tonumber(L, -1); //delayTicks
	lua_pop(L, 1);

	condvec.insert(condvec.begin(), CreatureCondition(ticks, condCount, magicTargetCondition));
}

void SpellScript::internalLoadTransformVec(lua_State *L, TransformMap& transformMap)
{
	TransformItem ti;
	ConditionVec condvec;

	int stateCount = (int)lua_tonumber(L, -1);
	lua_pop(L,1);

	for(int s = 0; s < stateCount; ++s) {
		condvec.clear();

		int id = (int)lua_tonumber(L, -1);
		lua_pop(L,1);

		ti.first = (int)lua_tonumber(L, -1);
		lua_pop(L,1);

		int count = (int)lua_tonumber(L, -1);
		lua_pop(L,1);

		for(int n = 0; n < count; ++n) {
			internalLoadDamageVec(L, condvec);
		}

		ti.second = condvec;
		transformMap[id] = ti;
	}
}

int SpellScript::luaActionManaShield(lua_State *L)
{
	long time = (long)lua_tonumber(L, -1)*1000;
	lua_pop(L,1);

	Spell* spell = getSpell(L);
	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L,1);
	creature->manaShieldTicks = time;

	Player* p = dynamic_cast<Player*>(creature);
	if(p)
	     p->sendIcons();
	return 0;
}

int SpellScript::luaActionChangeSpeed(lua_State *L){
	long time = (long)lua_tonumber(L, -1)*1000;
	lua_pop(L,1);

	int speed = (int)lua_tonumber(L, -1);
	lua_pop(L,1);

	Spell* spell = getSpell(L);
	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L,1);

	spell->game->addEvent(makeTask(time, boost::bind(&Game::changeSpeed, spell->game,creature->getID(), creature->getNormalSpeed()) ) );
	Player* p = dynamic_cast<Player*>(creature);
	if(p){
         spell->game->changeSpeed(creature->getID(), creature->getNormalSpeed()+speed);
	     p->sendIcons();
      }
    creature->hasteTicks = time;
	return 0;
}

int SpellScript::luaActionChangeSpeedMonster(lua_State *L){
	long time = (long)lua_tonumber(L, -1)*1000;
	lua_pop(L,1);

	int speed = (int)lua_tonumber(L, -1);
	lua_pop(L,1);

	Spell* spell = getSpell(L);
	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L,1);

	if(creature){
		spell->game->addEvent(makeTask(time, boost::bind(&Game::changeSpeed, spell->game,creature->getID(), creature->getSpeed())));
		spell->game->changeSpeed(creature->getID(), speed);
		creature->hasteTicks = time;
    }
	return 0;
}

int SpellScript::luaActionGetSpeed(lua_State *L){
	Spell* spell = getSpell(L);
	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L,1);

	lua_pushnumber(L, creature->getNormalSpeed());
	return 1;
}

int SpellScript::luaActionGetPos(lua_State *L){
	const char* s = lua_tostring(L, -1);
	lua_pop(L,1);
	Spell* spell = getSpell(L);
	Creature* c = spell->game->getCreatureByName(std::string(s));
	Player* p = dynamic_cast<Player*>(c);
	if(!c || !p){
      lua_newtable(L);
      lua_pushstring(L, "x");
      lua_pushnil(L);
      lua_settable(L, -3);

      lua_pushstring(L, "y");
      lua_pushnil(L);
      lua_settable(L, -3);

      lua_pushstring(L, "z");
      lua_pushnil(L);
      lua_settable(L, -3);
	}
	else{
         lua_newtable(L);
      lua_pushstring(L, "x");
      lua_pushnumber(L, c->pos.x);
      lua_settable(L, -3);

      lua_pushstring(L, "y");
      lua_pushnumber(L, c->pos.y);
      lua_settable(L, -3);

      lua_pushstring(L, "z");
      lua_pushnumber(L, c->pos.z);
      lua_settable(L, -3);
	}
	return 1;
}

// getAttackedCreaturePos(cid) — live pos of the caster's current attack target (battle list).
int SpellScript::luaActionGetAttackedCreaturePos(lua_State *L){
	Spell* spell = getSpell(L);
	Creature* caster = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L, 1);

	Creature* target = NULL;
	if(caster && caster->attackedCreature != 0)
		target = spell->game->getCreatureByID(caster->attackedCreature);

	lua_newtable(L);
	lua_pushstring(L, "x");
	if(target)
		lua_pushnumber(L, target->pos.x);
	else
		lua_pushnil(L);
	lua_settable(L, -3);

	lua_pushstring(L, "y");
	if(target)
		lua_pushnumber(L, target->pos.y);
	else
		lua_pushnil(L);
	lua_settable(L, -3);

	lua_pushstring(L, "z");
	if(target)
		lua_pushnumber(L, target->pos.z);
	else
		lua_pushnil(L);
	lua_settable(L, -3);
	return 1;
}

// getPlayerSkill(cid, skill): nivel de un skill del jugador (0 puños, 1 club, 2 sword, 3 axe,
// 4 distancia, 5 escudo, 6 pesca). -1 si cid no es un jugador o el skill no existe.
// Lo usan exori hur y exori con para escalar el daño con el skill, como en las versiones nuevas.
int SpellScript::luaActionGetPlayerSkill(lua_State *L)
{
	int skill = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	Player* player = spell ? dynamic_cast<Player*>(spell->game->getCreatureByID(cid)) : NULL;
	if(!player || skill < SKILL_FIST || skill > SKILL_FISH)
		lua_pushnumber(L, -1);
	else
		lua_pushnumber(L, (double)player->getSkill((skills_t)skill, SKILL_LEVEL));
	return 1;
}

// getPlayerWeapon(cid): arma en las manos (primero la derecha) como tabla
// {type = "sword" | "club" | "axe" | "dist" | "none", attack = n, id = n}.
// Escudos y lo que no es arma se saltean. Sin jugador o sin arma: type "none", attack 0, id 0.
int SpellScript::luaActionGetPlayerWeapon(lua_State *L)
{
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	Player* player = spell ? dynamic_cast<Player*>(spell->game->getCreatureByID(cid)) : NULL;
	const char* type = "none";
	int attack = 0;
	int id = 0;
	if(player) {
		for(int slot = SLOT_RIGHT; slot <= SLOT_LEFT; slot++) {
			Item* item = player->getItem(slot);
			if(!item)
				continue;
			const char* kind = NULL;
			switch(item->getWeaponType()) {
				case SWORD: kind = "sword"; break;
				case CLUB: kind = "club"; break;
				case AXE: kind = "axe"; break;
				case DIST: kind = "dist"; break;
				default: break;
			}
			if(!kind)
				continue;
			type = kind;
			id = item->getID();
			attack = Item::items[id].attack;
			break;
		}
	}

	lua_newtable(L);
	lua_pushstring(L, "type");
	lua_pushstring(L, type);
	lua_settable(L, -3);
	lua_pushstring(L, "attack");
	lua_pushnumber(L, attack);
	lua_settable(L, -3);
	lua_pushstring(L, "id");
	lua_pushnumber(L, id);
	lua_settable(L, -3);
	return 1;
}

// getCreatureDirection(cid): hacia dónde mira la criatura: "n", "e", "s" o "w" ("" si no existe).
// Lo usa exori min para armar el barrido de las 3 casillas de adelante: con needDirection el área no puede
// repetir las esquinas entre dos direcciones.
int SpellScript::luaActionGetCreatureDirection(lua_State *L)
{
	unsigned int cid = (unsigned int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	Creature* creature = spell ? spell->game->getCreatureByID(cid) : NULL;
	const char* dir = "";
	if(creature) {
		switch(creature->getDirection()) {
			case NORTH: dir = "n"; break;
			case EAST: dir = "e"; break;
			case SOUTH: dir = "s"; break;
			case WEST: dir = "w"; break;
			default: break;
		}
	}
	lua_pushstring(L, dir);
	return 1;
}

bool SpellScript::echoCast = false;
double SpellScript::echoScale = 1.0;

// echoReady(cid): segundos que faltan para poder lanzar el Eco (0 = listo). Si falta, avisa al jugador.
int SpellScript::luaActionEchoReady(lua_State *L)
{
	unsigned long cid = (unsigned long)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	Player* player = spell ? dynamic_cast<Player*>(spell->game->getCreatureByID(cid)) : NULL;
	int64_t left = 0;
	if(player) {
		std::map<unsigned long, EchoState>::iterator it = echoStates.find(cid);
		if(it != echoStates.end() && it->second.readyAt > OTSYS_TIME())
			left = (it->second.readyAt - OTSYS_TIME() + 999) / 1000;
		if(left > 0) {
			std::stringstream msg;
			msg << "You can use it again in " << left << " s.";
			spellFail(spell->game, player, msg.str());
		}
	}
	lua_pushnumber(L, (double)left);
	return 1;
}

// startEcho(cid, ventana_s, espera_s, escala, escala_pvp): deja el Eco activo `ventana_s` segundos; la
// próxima vez se puede lanzar dentro de `espera_s`. La repetición pega `escala` (o `escala_pvp` si el
// blanco es un jugador) del golpe original.
int SpellScript::luaActionStartEcho(lua_State *L)
{
	double pvpScale = lua_tonumber(L, -1);
	lua_pop(L, 1);
	double scale = lua_tonumber(L, -1);
	lua_pop(L, 1);
	int64_t cooldown = (int64_t)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int64_t window = (int64_t)lua_tonumber(L, -1);
	lua_pop(L, 1);
	unsigned long cid = (unsigned long)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	Player* player = spell ? dynamic_cast<Player*>(spell->game->getCreatureByID(cid)) : NULL;
	if(!player) {
		lua_pushboolean(L, false);
		return 1;
	}
	int64_t now = OTSYS_TIME();
	EchoState& st = echoStates[cid];
	st.activeUntil = now + window * 1000;
	st.readyAt = now + cooldown * 1000;
	st.scale = scale;
	st.pvpScale = pvpScale;
	// Ícono del cliente: encendido mientras espera el golpe, apagado hasta poder relanzarlo.
	std::stringstream ready;
	ready << spellTitle(spell->getName()) << ": ready again in " << cooldown << " s.";
	player->sendTextMessage(MSG_SMALLINFO, ready.str().c_str());
	std::stringstream msg;
	msg << "Your next strike will echo for " << window << " s.";
	player->sendTextMessage(MSG_INFO, msg.str().c_str());
	lua_pushboolean(L, true);
	return 1;
}

// attackSpeedReady(cid): segundos que faltan para volver a lanzar Frenzy / Rapid Fire (0 = listo). Si
// falta, se lo dice al jugador. Ver docs/gameplay/SPELL_ATTACK_SPEED.md.
int SpellScript::luaActionAttackSpeedReady(lua_State *L)
{
	unsigned long cid = (unsigned long)lua_tonumber(L, -1);
	lua_pop(L, 1);
	Spell* spell = getSpell(L);
	Player* player = spell ? dynamic_cast<Player*>(spell->game->getCreatureByID(cid)) : NULL;
	int64_t left = 0;
	if(player && player->attackSpeedReadyAt > OTSYS_TIME()) {
		left = (player->attackSpeedReadyAt - OTSYS_TIME() + 999) / 1000;
		std::stringstream msg;
		msg << "You can use it again in " << left << " s.";
		spellFail(spell->game, player, msg.str());
	}
	lua_pushnumber(L, (double)left);
	return 1;
}

// startAttackSpeed(cid, duracion_s, porcentaje, espera_s, efecto): durante `duracion_s` la espera entre
// golpes baja `porcentaje` % (nunca menos de ATTACK_SPEED_BUFF_MIN_DELAY_MS) y cada segundo sale `efecto`
// (NM_ME_*, NM_ME_NONE = ninguno) sobre el jugador; se puede volver a lanzar a los `espera_s` segundos.
// Vale para melee y distancia (checkCreatureAttacking usa getAttackDelayMs). El mensaje "Your attacks speed
// up for N s." lo lee el cliente (game_healthinfo) para prender el ícono con la cuenta regresiva.
int SpellScript::luaActionStartAttackSpeed(lua_State *L)
{
	int effect = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int64_t cooldown = (int64_t)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int percent = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);
	int64_t duration = (int64_t)lua_tonumber(L, -1);
	lua_pop(L, 1);
	unsigned long cid = (unsigned long)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Spell* spell = getSpell(L);
	Player* player = spell ? dynamic_cast<Player*>(spell->game->getCreatureByID(cid)) : NULL;
	if(!player || percent <= 0 || percent >= 100 || duration <= 0) {
		lua_pushboolean(L, false);
		return 1;
	}
	int64_t now = OTSYS_TIME();
	player->attackSpeedUntil = now + duration * 1000;
	player->attackSpeedPercent = percent;
	player->attackSpeedReadyAt = now + (cooldown > duration ? cooldown : duration) * 1000;
	player->attackSpeedEffect = (effect >= 0 && effect < 255) ? effect : -1;
	std::stringstream ready;                 // el cliente deja el ícono apagado hasta que se pueda relanzar
	ready << spellTitle(spell->getName()) << ": ready again in " << (cooldown > duration ? cooldown : duration) << " s.";
	player->sendTextMessage(MSG_SMALLINFO, ready.str().c_str());
	std::stringstream msg;
	msg << "Your attacks speed up for " << duration << " s.";
	player->sendTextMessage(MSG_SMALLINFO, msg.str().c_str());
	lua_pushboolean(L, true);
	return 1;
}

// Después de un hechizo que salió bien: si el jugador tiene el Eco activo y el hechizo admite eco, lo
// consume y programa la repetición contra el blanco de ahora.
void SpellScript::onPlayerSpellCast(Game* game, Player* player, Spell* spell, const std::string& var)
{
	if(!game || !player || !spell || !spell->isEchoable())
		return;
	InstantSpell* instant = dynamic_cast<InstantSpell*>(spell);
	std::map<unsigned long, EchoState>::iterator it = echoStates.find(player->getID());
	if(!instant || it == echoStates.end() || it->second.activeUntil == 0)
		return;
	bool active = OTSYS_TIME() <= it->second.activeUntil;
	it->second.activeUntil = 0;
	if(!active)
		return;

	game->addEvent(makeTask(ECHO_DELAY_MS, boost::bind(&SpellScript::castEcho, _1, player->getID(),
		instant->getWords(), var, (unsigned long)player->attackedCreature, it->second.scale, it->second.pvpScale)));
	sendSpellMagicEffect(game, player->pos, ECHO_EFFECT);
	player->sendTextMessage(MSG_SMALLINFO, "Your strike echoes.");   // el cliente apaga el ícono del Eco
}

// La repetición: el mismo hechizo, sin maná ni espera, con el daño escalado. Si el jugador cambió de
// blanco (o ya no existe) el eco se pierde; si el blanco quedó fuera de alcance, el script devuelve false.
void SpellScript::castEcho(Game* game, unsigned long playerId, std::string words, std::string var,
	unsigned long targetId, double scale, double pvpScale)
{
	OTSYS_THREAD_LOCK_CLASS lockClass(game->gameLock, "SpellScript::castEcho()");

	Player* player = dynamic_cast<Player*>(game->getCreatureByID(playerId));
	if(!player || player->isRemoved)
		return;
	std::map<std::string, Spell*>::iterator sit = spells.getAllSpells()->find(words);
	if(sit == spells.getAllSpells()->end())
		return;
	if(targetId != 0 && (unsigned long)player->attackedCreature != targetId) {
		player->sendTextMessage(MSG_SMALLINFO, "The echo fades: you changed target.");
		return;
	}
	Creature* target = targetId ? game->getCreatureByID(targetId) : NULL;
	echoCast = true;
	echoScale = dynamic_cast<Player*>(target) ? pvpScale : scale;
	bool ok = safeCast(sit->second, player, player->pos, var);
	echoCast = false;
	echoScale = 1.0;
	if(ok)
		sendSpellMagicEffect(game, player->pos, ECHO_EFFECT);
	else
		player->sendTextMessage(MSG_SMALLINFO, "The echo fades.");
}

int SpellScript::luaActionMakeRune(lua_State *L){
	unsigned char charges = (unsigned char)lua_tonumber(L, -1);
	lua_pop(L,1);

	unsigned short type = (unsigned short)lua_tonumber(L, -1);
	lua_pop(L,1);

	Spell* spell = getSpell(L);
	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L,1);

	Player* player = dynamic_cast<Player*>(creature);
	if(player){
		MagicEffectTargetClass magicTarget;

		magicTarget.offensive = false;
		magicTarget.drawblood = false;
		magicTarget.animationEffect = 0;
		magicTarget.attackType = ATTACK_NONE;
		magicTarget.hitEffect = 255; //NM_ME_NONE
		magicTarget.animationColor = 19; //GREEN

		int a = -1;
		int b = -1;
		bool missingSoul = false;
		unsigned short spentSoul = 0;
		unsigned short availableSoul = player->getSoul();
		Tile* tile = spell->game->getTile(player->pos);
		const bool gm = player->access >= g_config.ACCESS_PROTECT;   // GM: sin mana ni soul
		const bool requireSoul = !gm && (tile && tile->isPz());

		//try to create rune 1
		a = internalMakeRune(player, SLOT_RIGHT, spell, type, charges, requireSoul, availableSoul);
		if(a == 1) {
			magicTarget.manaCost = spell->getMana();
			if(requireSoul) {
				++spentSoul;
				--availableSoul;
			}
		}
		else if(a == -2) {
			missingSoul = true;
		}

		//check if we got enough mana for the left hand
		if(gm || player->getMana() - magicTarget.manaCost >= magicTarget.manaCost) {
			//try to create rune 2
			b = internalMakeRune(player, SLOT_LEFT, spell, type, charges, requireSoul, availableSoul);
			if(b == 1) {
				magicTarget.manaCost += spell->getMana();
				if(requireSoul) {
					++spentSoul;
					--availableSoul;
				}
			}
			else if(b == -2) {
				missingSoul = true;
			}
		}

		if(a == -1 && b == -1){ //not enough mana
			magicTarget.damageEffect = 2; //NM_ME_PUFF
			magicTarget.manaCost = player->getPlayerInfo(PLAYERINFO_MAXMANA) + 1; //force not enough mana
		}
		else if(missingSoul && a != 1 && b != 1) {
			magicTarget.damageEffect = 2; //NM_ME_PUFF
			magicTarget.manaCost = 0;
			player->sendCancel("You do not have enough soul.");
		}
		else if( a == 0 && b == 0){ //not create any rune
			magicTarget.damageEffect = 2; //NM_ME_PUFF
			magicTarget.manaCost = 0;
		}
		else if(a == 1 || b == 1) {
			magicTarget.damageEffect = 12; //NM_ME_MAGIC_ENERGIE = 12
		}

		bool isSuccess = spell->game->creatureThrowRune(player, player->pos, magicTarget);
		if(isSuccess && spentSoul > 0) {
			player->spendSoul(spentSoul);
		}

		lua_pushnumber(L, 1);
		return 1;
	}
	lua_pushnumber(L, 0);
	return 1;
}

//create new runes and delete blank ones
int SpellScript::internalMakeRune(Player *p, unsigned short sl_id, Spell *S, unsigned short id,
	unsigned char charges, bool requireSoul, unsigned short availableSoul){
	//check mana (el GM no paga mana ni espera, como en creatureMakeMagic)
	if(p->access < g_config.ACCESS_PROTECT && (p->mana < S->getMana() || PlayerExhaust::isExhausted(p)))
		return -1;
	Item *item = p->getItem(sl_id);
	if(item){
		if(item->getID() == ITEM_RUNE_BLANK){
			if(requireSoul && availableSoul == 0)
				return -2;
			// Player-made runes get 3 extra charges over store-bought ones.
			int craftedCharges = (int)charges + 3;
			if(craftedCharges > 255)
				craftedCharges = 255;
			p->addItemInventory(Item::CreateItem(id, (unsigned char)craftedCharges), sl_id);
			return 1;
		}
		else{
			return 0;
		}
	}
	else{
		return 0;
	}
	return 0;
}

int SpellScript::luaActionMakeArrows(lua_State *L){
	unsigned char count = (unsigned char)lua_tonumber(L, -1);
	lua_pop(L,1);

	unsigned short id = (unsigned short)lua_tonumber(L, -1);
	lua_pop(L,1);

	Spell* spell = getSpell(L);
	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L,1);

	Player* player = dynamic_cast<Player*>(creature);
	if(player){
 		MagicEffectTargetClass magicTarget;

		magicTarget.offensive = false;
 		magicTarget.drawblood = false;
 		magicTarget.animationEffect = 0;
 		magicTarget.attackType = ATTACK_NONE;
 		magicTarget.hitEffect = 255; //NM_ME_NONE
 		magicTarget.animationColor = 19; //GREEN

		Tile* tile = spell->game->getTile(player->pos);
		const bool gm = player->access >= g_config.ACCESS_PROTECT;   // GM: sin mana ni soul
		const bool requireSoul = !gm && (tile && tile->isPz());

		if(!gm && player->mana < spell->getMana()){
			magicTarget.damageEffect = 2; //NM_ME_PUFF
  			magicTarget.manaCost = player->getPlayerInfo(PLAYERINFO_MAXMANA) + 1; //force not enough mana
		}
		else if(requireSoul && player->getSoul() == 0) {
			magicTarget.damageEffect = 2; //NM_ME_PUFF
			magicTarget.manaCost = 0;
			player->sendCancel("You do not have enough soul.");
		}
		else{
			magicTarget.manaCost = spell->getMana();
			magicTarget.damageEffect = 12; //NM_ME_MAGIC_ENERGIE = 12
 		}

		bool isSuccess = spell->game->creatureThrowRune(player, player->pos, magicTarget);

		if(isSuccess) {
			Item* new_item = Item::CreateItem(id,count);
			if(!player->addItem(new_item)){
				spell->game->addThing(NULL,player->pos,new_item);
			}
			if(requireSoul)
				player->spendSoul(1);
		}

 		lua_pushnumber(L, 1);
 		return 1;
	}
	lua_pushnumber(L, 0);
	return 1;
}

int SpellScript::luaActionMakeFood(lua_State *L){
	unsigned char count = (unsigned char)lua_tonumber(L, -1);
	lua_pop(L,1);

	Spell* spell = getSpell(L);
	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L,1);

	Player* player = dynamic_cast<Player*>(creature);
	if(player){
  		MagicEffectTargetClass magicTarget;

		magicTarget.offensive = false;
		magicTarget.drawblood = false;
		magicTarget.animationEffect = 0;
		magicTarget.attackType = ATTACK_NONE;
		magicTarget.hitEffect = 255; //NM_ME_NONE
		magicTarget.animationColor = 19; //GREEN

		if(player->mana < spell->getMana()){
  			magicTarget.damageEffect = 2; //NM_ME_PUFF
    		magicTarget.manaCost = player->getPlayerInfo(PLAYERINFO_MAXMANA) + 1; //force not enough mana
  		}
  		else{
  			magicTarget.manaCost = spell->getMana();
  			magicTarget.damageEffect = 12; //NM_ME_MAGIC_ENERGIE = 12
		}

		bool isSuccess = spell->game->creatureThrowRune(player, player->pos, magicTarget);

		if(isSuccess) {
			int r,foodtype;
			r = rand()%8;
			if(r == 0) foodtype = ITEM_MEAT;
			else if(r == 1) foodtype = ITEM_HAM;
			else if(r == 2) foodtype = ITEM_GRAPE;
			else if(r == 3) foodtype = ITEM_APPLE;
			else if(r == 4) foodtype = ITEM_BREAD;
			else if(r == 5) foodtype = ITEM_CHEESE;
			else if(r == 6) foodtype = ITEM_ROLL;
			else foodtype = ITEM_BREAD;

			Item* new_item = Item::CreateItem(foodtype,count);
			if(!player->addItem(new_item)){
				spell->game->addThing(NULL,player->pos,new_item);
			}
		}

		lua_pushnumber(L, isSuccess ? 1 : 0);
		return 1;
	}
	lua_pushnumber(L, 0);
	return 1;
}

int SpellScript::luaSetPlayerLightLevel(lua_State* L)
{
	int id = (int)lua_tonumber(L, -2);
	int lvl = (int)lua_tonumber(L, -1);
	lua_pop(L,2);

	Spell* spell = getSpell(L);
	Creature* c = spell->game->getCreatureByID(id);
	Player* player = c? dynamic_cast<Player*>(c) : NULL;

	if (player)
		spell->game->creatureChangeLight(player, 0, lvl, 0xD7);

	return 0;
}

int SpellScript::luaActionInvisible(lua_State *L)
{
	long time = (long)lua_tonumber(L, -1)*1000;
	lua_pop(L,1);

	Spell* spell = getSpell(L);
	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L,1);

	creature->setInvisible(time);
	spell->game->creatureChangeOutfit(creature);
	return 0;
}

int SpellScript::luaActionReduceExhaustion(lua_State *L)
{
	Spell* spell = getSpell(L);
	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L,1);

	Player* player = creature ? dynamic_cast<Player*>(creature) : NULL;
	if(player && player->access < g_config.ACCESS_PROTECT && !echoCast){
		PlayerExhaust::cap(player, g_config.EXHAUSTED / 2);
	}
	return 0;
}

int SpellScript::luaActionReduceExhaustionByPercent(lua_State *L)
{
	int percent = (int)lua_tonumber(L, -1);
	lua_pop(L,1);

	Spell* spell = getSpell(L);
	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L,1);

	Player* player = creature ? dynamic_cast<Player*>(creature) : NULL;
	if(player && player->access < g_config.ACCESS_PROTECT){
		long newExhaust = (long)(g_config.EXHAUSTED * percent / 100.0);
		PlayerExhaust::cap(player, (int)newExhaust);
	}
	return 0;
}

int SpellScript::luaActionSkillBuff(lua_State *L)
{
	int bonus = (int)lua_tonumber(L, -1);
	lua_pop(L,1);

	long time = (long)lua_tonumber(L, -1) * 1000;
	lua_pop(L,1);

	Spell* spell = getSpell(L);
	if(!spell){
		return 0;
	}

	Creature* creature = spell->game->getCreatureByID((unsigned long)lua_tonumber(L, -1));
	lua_pop(L,1);

	Player* player = creature ? dynamic_cast<Player*>(creature) : NULL;
	// También a los GM (antes no: con un GM el hechizo no hacía nada ni prendía el ícono, nov 2026).
	if(player){
		// Refresh duration/bonus on every successful cast; player must recast
		// after it expires to get the skill boost again.
		player->tempoBuffTicks = time;
		player->tempoBuffBonus = bonus;
		player->sendSkills();
		// el cliente prende el ícono con este texto y lo apaga con "Your skills return to normal." (game.cpp)
		std::stringstream msg;
		msg << "Your skills rise by " << bonus << " for " << spellSeconds(time) << " s.";
		player->sendTextMessage(MSG_INFO, msg.str().c_str());
	}
	return 0;
}
