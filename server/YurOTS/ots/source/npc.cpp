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
#include <sstream>
#include <fstream>
#include <vector>

#include <libxml/xmlmemory.h>
#include <libxml/parser.h>

#include "npc.h"
#include "ioaccount.h"
#include "ioplayer.h"
#include "luascript.h"
#include "player.h"
#include "item.h"
#include <cctype>
#include <map>

struct PendingTransaction {
	int cid;
	int itemid;
	int count;
	int cost;
	bool isSell;
	bool isBulkSell;
	std::vector<std::pair<int,int> > bulkItems;
	std::string bulkLabel;
	PendingTransaction() : cid(0), itemid(0), count(0), cost(0), isSell(false), isBulkSell(false) {}
};

static std::map<unsigned long, PendingTransaction> pendingTrades;

enum BankActionResult {
	BANK_ACTION_SUCCESS = 1,
	BANK_ACTION_INVALID_AMOUNT = -1,
	BANK_ACTION_PLAYER_NOT_FOUND = -2,
	BANK_ACTION_ACCOUNT_NOT_FOUND = -3,
	BANK_ACTION_NOT_ENOUGH_MONEY = -4,
	BANK_ACTION_NOT_ENOUGH_BALANCE = -5,
	BANK_ACTION_TARGET_NOT_FOUND = -6,
	BANK_ACTION_SAME_ACCOUNT = -7,
	BANK_ACTION_SAVE_FAILED = -8
};

static bool loadAccountByNumber(unsigned long accountNumber, Account& account)
{
	account = IOAccount::instance()->loadAccount(accountNumber);
	return account.accnumber == accountNumber;
}

static bool resolvePlayerAccountByName(const std::string& name, Account& account)
{
	Player target(name, NULL);
	if(!IOPlayer::instance()->loadPlayer(&target, name))
		return false;

	return loadAccountByNumber((unsigned long)target.getAccount(), account);
}

static void addMoneyToPlayer(Player* player, uint64_t amount)
{
	while(amount >= 10000) {
		const uint64_t crystalCount = std::min<uint64_t>(amount / 10000, 100);
		player->TLMaddItem(ITEM_COINS_CRYSTAL, (unsigned char)crystalCount);
		amount -= crystalCount * 10000;
	}

	while(amount >= 100) {
		const uint64_t platinumCount = std::min<uint64_t>(amount / 100, 100);
		player->TLMaddItem(ITEM_COINS_PLATINUM, (unsigned char)platinumCount);
		amount -= platinumCount * 100;
	}

	if(amount > 0)
		player->TLMaddItem(ITEM_COINS_GOLD, (unsigned char)amount);
}

static bool persistPlayerState(Player* player)
{
	return player && IOPlayer::instance()->savePlayer(player);
}

static void resetPendingTrade(PendingTransaction& trade)
{
	trade = PendingTransaction();
}

static PendingTransaction& preparePendingTrade(unsigned long npcId)
{
	PendingTransaction& trade = pendingTrades[npcId];
	resetPendingTrade(trade);
	return trade;
}

static bool clearPendingTrade(unsigned long npcId, int cid = 0)
{
	std::map<unsigned long, PendingTransaction>::iterator it = pendingTrades.find(npcId);
	if(it == pendingTrades.end())
		return false;

	if(cid != 0 && it->second.cid != cid)
		return false;

	pendingTrades.erase(it);
	return true;
}

extern LuaScript g_config;

AutoList<Npc> Npc::listNpc;

Npc::Npc(const std::string& name, Game* game) :
 Creature()
{
	char *tmp;
	useCount = 0;
	this->loaded = false;
	this->name = name;
	std::string datadir = g_config.getGlobalString("datadir");
	std::string filename = datadir + "npc/" + std::string(name) + ".xml";
	std::transform(filename.begin(), filename.end(), filename.begin(), tolower);
	xmlDocPtr doc = xmlParseFile(filename.c_str());
	if(doc){
		this->loaded=true;
		xmlNodePtr root, p;
		root = xmlDocGetRootElement(doc);

		if (xmlStrcmp(root->name,(const xmlChar*) "npc")){
		//TODO: use exceptions here
		std::cerr << "Malformed XML" << std::endl;
		}

		p = root->children;

		tmp = (char*)xmlGetProp(root, (const xmlChar *)"script");
		if(tmp){
			this->scriptname = tmp;
			xmlFreeOTSERV(tmp);
		}
		else{
			this->scriptname = "";
		}

		if(tmp = (char*)xmlGetProp(root, (const xmlChar *)"name")) {
			this->name = tmp;
			xmlFreeOTSERV(tmp);
		}
		else{
			this->name = "";
		}

		if(tmp = (char*)xmlGetProp(root, (const xmlChar *)"access")) {
			access = atoi(tmp);
			xmlFreeOTSERV(tmp);
		}
		else{
			access = 0;
		}

		if(tmp = (char*)xmlGetProp(root, (const xmlChar *)"level")) {
			level = atoi(tmp);
			xmlFreeOTSERV(tmp);
			setNormalSpeed();
			//std::cout << level << std::endl;
		}
		else{
			level = 1;
		}

		if(tmp = (char*)xmlGetProp(root, (const xmlChar *)"maglevel")) {
			maglevel = atoi(tmp);
			xmlFreeOTSERV(tmp);
			//std::cout << maglevel << std::endl;
		}
		else{
			maglevel = 1;
		}

		while (p)
		{
			const char* str = (char*)p->name;
			if(strcmp(str, "mana") == 0){
				if(tmp = (char*)xmlGetProp(p, (const xmlChar *)"now")) {
					this->mana = atoll(tmp);
					xmlFreeOTSERV(tmp);
				}
				else{
					this->mana = 100;
				}
				if(tmp = (char*)xmlGetProp(p, (const xmlChar *)"max")) {
					this->manamax = atoll(tmp);
					xmlFreeOTSERV(tmp);
				}
				else{
					this->manamax = 100;
				}
			}
			if(strcmp(str, "health") == 0){
				if(tmp = (char*)xmlGetProp(p, (const xmlChar *)"now")) {
					this->health = atoi(tmp);
					xmlFreeOTSERV(tmp);
				}
				else{
					this->health = 100;
				}
				if(tmp = (char*)xmlGetProp(p, (const xmlChar *)"max")) {
					this->healthmax = atoi(tmp);
					xmlFreeOTSERV(tmp);
				}
				else{
					this->healthmax = 100;
				}
			}
			if(strcmp(str, "look") == 0){
				if(tmp = (char*)xmlGetProp(p, (const xmlChar *)"type")) {
					this->looktype = atoi(tmp);
					xmlFreeOTSERV(tmp);
				}
				else{
					this->looktype = 20;
				}
				this->lookmaster = this->looktype;
				if(tmp = (char*)xmlGetProp(p, (const xmlChar *)"head")) {
					this->lookhead = atoi(tmp);
					xmlFreeOTSERV(tmp);
				}
				else{
					this->lookhead = 10;
				}

				if(tmp = (char*)xmlGetProp(p, (const xmlChar *)"body")) {
					this->lookbody = atoi(tmp);
					xmlFreeOTSERV(tmp);
				}
				else{
					this->lookbody = 20;
				}

				if(tmp = (char*)xmlGetProp(p, (const xmlChar *)"legs")) {
					this->looklegs = atoi(tmp);
					xmlFreeOTSERV(tmp);
				}
				else{
					this->looklegs = 30;
				}

				if(tmp = (char*)xmlGetProp(p, (const xmlChar *)"feet")) {
					this->lookfeet = atoi(tmp);
					xmlFreeOTSERV(tmp);
				}
				else{
					this->lookfeet = 40;
				}
				if(tmp = (char*)xmlGetProp(p, (const xmlChar *)"corpse")) {
					this->lookcorpse = atoi(tmp);
					xmlFreeOTSERV(tmp);
				}
				else{
					this->lookcorpse = 100;
				}

			}
			if(strcmp(str, "attack") == 0){
				if(tmp = (char*)xmlGetProp(p, (const xmlChar *)"type")){
					std::string attacktype = tmp;
					xmlFreeOTSERV(tmp);
					if(attacktype == "melee")
						this->fighttype = FIGHT_MELEE;
					tmp = (char*)xmlGetProp(p, (const xmlChar *)"damage");
					if(tmp){
						this->damage = atoi(tmp);
						xmlFreeOTSERV(tmp);
					}
					else{
						this->damage = 5;
					}
				}
				else{
					this->fighttype = FIGHT_MELEE;
					this->damage = 0;
				}
			}
			if(strcmp(str, "loot") == 0){
				//TODO implement loot
			}

			p = p->next;
		}

		xmlFreeDoc(doc);
	}
	//now try to load the script
	this->script = new NpcScript(this->scriptname, this);
	if(!this->script->isLoaded())
		this->loaded=false;
	this->game=game;
}


Npc::~Npc()
{
	clearPendingTrade(this->getID());
	delete this->script;
}

std::string Npc::getDescription(bool self) const
{
	std::stringstream s;
	std::string str;
	s << name << ".";
	str = s.str();
	return str;
}

void Npc::onThingMove(const Player *player, const Thing *thing, const Position *oldPos,
	unsigned char oldstackpos, unsigned char oldcount, unsigned char count){
	//not yet implemented
}

void Npc::onCreatureAppear(const Creature *creature){
	this->script->onCreatureAppear(creature->getID());
}

void Npc::onCreatureDisappear(const Creature *creature, unsigned char stackPos, bool tele){
	clearPendingTrade(this->getID(), (int)creature->getID());
	this->script->onCreatureDisappear(creature->getID());
}

void Npc::onThingDisappear(const Thing* thing, unsigned char stackPos){
	const Creature *creature = dynamic_cast<const Creature*>(thing);
	if(creature){
		clearPendingTrade(this->getID(), (int)creature->getID());
		this->script->onCreatureDisappear(creature->getID());
	}
}
void Npc::onThingAppear(const Thing* thing){
	const Creature *creature = dynamic_cast<const Creature*>(thing);
	if(creature)
		this->script->onCreatureAppear(creature->getID());
}

void Npc::onCreatureTurn(const Creature *creature, unsigned char stackpos){
	//not implemented yet, do we need it?
}

/*
void Npc::setAttackedCreature(unsigned long id){
	//not implemented yet
}
*/

void Npc::onCreatureSay(const Creature *creature, SpeakClasses type, const std::string &text){
	if(creature->getID() == this->getID())
		return;

	std::map<unsigned long, PendingTransaction>::iterator it = pendingTrades.find(this->getID());
	if(it != pendingTrades.end() && it->second.cid == (int)creature->getID()){
		std::string lower = text;
		std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
		if(lower == "yes" || lower == "si" || lower == "sí" || lower == "sip" || lower == "dale" || lower == "y"){
			Player* player = dynamic_cast<Player*>(game->getCreatureByID(creature->getID()));
			if(player){
				PendingTransaction& pt = it->second;
				if(pt.isSell){
					if(pt.isBulkSell){
						bool hasAll = true;
						for(size_t i = 0; i < pt.bulkItems.size(); i++){
							if(!player->getItem(pt.bulkItems[i].first, pt.bulkItems[i].second))
								hasAll = false;
						}
						if(hasAll){
							for(size_t i = 0; i < pt.bulkItems.size(); i++){
								player->removeItem(pt.bulkItems[i].first, pt.bulkItems[i].second);
							}
							player->payBack(pt.cost);
							doSay("Thanks! Here is your gold.");
						}else
							doSay("Sorry, you do not have those items.");
					}else if(player->getItem(pt.itemid, pt.count)){
						if(player->removeItem(pt.itemid, pt.count)){
							player->payBack(pt.cost);
							doSay("Thanks! Here is your gold.");
						}else
							doSay("Sorry, you do not have that item.");
					}else
						doSay("Sorry, you do not have that item.");
				}else{
					if(player->canPayWithBank(pt.cost)){
						if(player->removeCoinsWithBank(pt.cost)){
							player->TLMaddItem(pt.itemid, pt.count);
							doSay("Here you go!");
						}else
							doSay("Sorry, you do not have enough gold.");
					}else
						doSay("Sorry, you do not have enough gold.");
				}
			}
			pendingTrades.erase(it);
			return;
		}else if(lower == "no" || lower == "n" || lower == "nop"){
			doSay("No problem! Maybe next time.");
			pendingTrades.erase(it);
			return;
		}
	}

	this->script->onCreatureSay(creature->getID(), type, text);
}

void Npc::onCreatureChangeOutfit(const Creature* creature){
	#ifdef __DEBUG_NPC__
		std::cout << "Npc::onCreatureChangeOutfit" << std::endl;
	#endif
	//we dont care about filthy player changing his ugly clothes
}

int Npc::onThink(int& newThinkTicks){
	this->script->onThink();
	return Creature::onThink(newThinkTicks);
}


void Npc::doSay(std::string msg){
	if(!game->creatureSaySpell(this, msg))
		this->game->creatureSay(this, SPEAK_SAY, msg);
}

void Npc::doAttack(int id){
	attackedCreature = id;
}

void Npc::doMove(int direction){
	switch(direction){
		case 0:
			this->game->thingMove(this, this,this->pos.x, this->pos.y+1, this->pos.z, 1);
		break;
		case 1:
			this->game->thingMove(this, this,this->pos.x+1, this->pos.y, this->pos.z, 1);
		break;
		case 2:
			this->game->thingMove(this, this,this->pos.x, this->pos.y-1, this->pos.z, 1);
		break;
		case 3:
			this->game->thingMove(this, this,this->pos.x-1, this->pos.y, this->pos.z, 1);
		break;
	}
}

void Npc::doMoveTo(Position target){
	if(route.size() == 0 || route.back() != target || route.front() != this->pos){
		route = this->game->getPathTo(this, this->pos, target);
	}
	if(route.size()==0){
		//still no route, means there is none
		return;
	}
	else route.pop_front();
	Position nextStep=route.front();
	route.pop_front();
	int dx = nextStep.x - this->pos.x;
	int dy = nextStep.y - this->pos.y;
	this->game->thingMove(this, this,this->pos.x + dx, this->pos.y + dy, this->pos.z, 1);
}

NpcScript::NpcScript(std::string scriptname, Npc* npc){
	this->npc = NULL;
	this->loaded = false;
	if(scriptname == "")
		return;
	luaState = lua_open();
	luaL_openlibs(luaState);

	std::string datadir = g_config.getGlobalString("datadir");
    lua_dofile(luaState, std::string(datadir + "npc/scripts/lib/npc.lua").c_str());

#ifdef USING_VISUAL_2005
	FILE* in = NULL;
	fopen_s(&in, scriptname.c_str(), "r");
#else
	FILE* in=fopen(scriptname.c_str(), "r");
#endif //USING_VISUAL_2005

	if(!in)
		return;
	else
		fclose(in);
	lua_dofile(luaState, scriptname.c_str());
	this->loaded=true;
	this->npc=npc;
	this->setGlobalNumber("addressOfNpc", (int)npc);
	this->registerFunctions();
}

void NpcScript::onThink(){
	lua_pushstring(luaState, "onThink");
	lua_gettable(luaState, LUA_GLOBALSINDEX);
	if(lua_pcall(luaState, 0, 0, 0)){
		std::cerr << "NpcScript: onThink: lua error: " << lua_tostring(luaState, -1) << std::endl;
		lua_pop(luaState,1);
		std::cerr << "Backtrace: " << std::endl;
		lua_Debug* d = NULL;
		int i = 0;
		while(lua_getstack(luaState, i++, d)){
			std::cerr << "    " << d->name << " @ " << d->currentline << std::endl;
		}
	}
}


void NpcScript::onCreatureAppear(unsigned long cid){
	if(npc->getID() != cid){
		lua_pushstring(luaState, "onCreatureAppear");
		lua_gettable(luaState, LUA_GLOBALSINDEX);
		lua_pushnumber(luaState, cid);
		if(lua_pcall(luaState, 1, 0, 0)){
			std::cerr << "NpcScript: onCreatureAppear: lua error: " << lua_tostring(luaState, -1) << std::endl;
			lua_pop(luaState,1);
			std::cerr << "Backtrace: " << std::endl;
			lua_Debug* d = NULL;
			int i = 0;
			while(lua_getstack(luaState, i++, d)){
				std::cerr << "    " << d->name << " @ " << d->currentline << std::endl;
			}
		}
	}
}

void NpcScript::onCreatureDisappear(int cid){
	lua_pushstring(luaState, "onCreatureDisappear");
	lua_gettable(luaState, LUA_GLOBALSINDEX);
	lua_pushnumber(luaState, cid);
	if(lua_pcall(luaState, 1, 0, 0)){
		std::cerr << "NpcScript: onCreatureDisappear: lua error: " << lua_tostring(luaState, -1) << std::endl;
		lua_pop(luaState,1);
		std::cerr << "Backtrace: " << std::endl;
		lua_Debug* d = NULL;
		int i = 0;
		while(lua_getstack(luaState, i++, d)){
			std::cerr << "    " << d->name << " @ " << d->currentline << std::endl;
		}
	}
}

void NpcScript::onCreatureSay(int cid, SpeakClasses type, const std::string &text)
{
	if (!npc->game->getPlayerByID(cid))		// Tibia Rules' fix
		return;

	//now we need to call the function
	lua_pushstring(luaState, "onCreatureSay");
	lua_gettable(luaState, LUA_GLOBALSINDEX);
	lua_pushnumber(luaState, cid);
	lua_pushnumber(luaState, type);
	lua_pushstring(luaState, text.c_str());
	if(lua_pcall(luaState, 3, 0, 0)){
		std::cerr << "NpcScript: onCreatureSay: lua error: " << lua_tostring(luaState, -1) << std::endl;
		lua_pop(luaState,1);
		std::cerr << "Backtrace: " << std::endl;
		lua_Debug* d = NULL;
		int i = 0;
		while(lua_getstack(luaState, i++, d)){
			std::cerr << "    " << d->name << " @ " << d->currentline << std::endl;
		}
	}
}

int NpcScript::registerFunctions()
{
	lua_register(luaState, "selfSay", NpcScript::luaActionSay);
	lua_register(luaState, "doPlayerSendTextMessage", NpcScript::luaDoPlayerSendTextMessage);
	lua_register(luaState, "selfMove", NpcScript::luaActionMove);
	lua_register(luaState, "selfMoveTo", NpcScript::luaActionMoveTo);
	lua_register(luaState, "selfGetPosition", NpcScript::luaSelfGetPos);
	lua_register(luaState, "selfAttackCreature", NpcScript::luaActionAttackCreature);
	lua_register(luaState, "creatureGetName", NpcScript::luaCreatureGetName);
	lua_register(luaState, "creatureGetName2", NpcScript::luaCreatureGetName2);
	lua_register(luaState, "creatureGetPosition", NpcScript::luaCreatureGetPos);
	lua_register(luaState, "selfGetPosition", NpcScript::luaSelfGetPos);

#ifdef TLM_BUY_SELL
	lua_register(luaState, "buy", NpcScript::luaBuyItem);
	lua_register(luaState, "sell", NpcScript::luaSellItem);
	lua_register(luaState, "sellBundle", NpcScript::luaSellBundle);
	lua_register(luaState, "cancelPendingTrade", NpcScript::luaCancelPendingTrade);
	lua_register(luaState, "pay", NpcScript::luaPayMoney);
#endif

#ifdef YUR_NPC_EXT
	lua_register(luaState, "getPlayerStorageValue", NpcScript::luaGetPlayerStorageValue);
	lua_register(luaState, "setPlayerStorageValue", NpcScript::luaSetPlayerStorageValue);
	lua_register(luaState, "doPlayerRemoveItem", NpcScript::luaPlayerRemoveItem);
	lua_register(luaState, "doPlayerAddItem", NpcScript::luaPlayerAddItem);
	lua_register(luaState, "getPlayerLevel", NpcScript::luaGetPlayerLevel);
	lua_register(luaState, "getPlayerItemCount", NpcScript::luaGetPlayerItemCount);
	lua_register(luaState, "getPlayerMoney", NpcScript::luaGetPlayerMoney);
	lua_register(luaState, "getPlayerBankBalance", NpcScript::luaGetPlayerBankBalance);
	lua_register(luaState, "doPlayerDepositMoney", NpcScript::luaDepositPlayerMoney);
	lua_register(luaState, "doPlayerWithdrawMoney", NpcScript::luaWithdrawPlayerMoney);
	lua_register(luaState, "doPlayerTransferMoneyTo", NpcScript::luaTransferPlayerMoneyTo);
	lua_register(luaState, "getPlayerVocation", NpcScript::luaGetPlayerVocation);
	lua_register(luaState, "setPlayerMasterPos", NpcScript::luaSetPlayerMasterPos);
#endif //YUR_NPC_EXT

#ifdef YUR_GUILD_SYSTEM
	lua_register(luaState, "foundNewGuild", NpcScript::luaFoundNewGuild);
	lua_register(luaState, "getPlayerGuildStatus", NpcScript::luaGetPlayerGuildStatus);
	lua_register(luaState, "setPlayerGuildStatus", NpcScript::luaSetPlayerGuildStatus);
	lua_register(luaState, "getPlayerGuildName", NpcScript::luaGetPlayerGuildName);
	lua_register(luaState, "setPlayerGuild", NpcScript::luaSetPlayerGuild);
	lua_register(luaState, "clearPlayerGuild", NpcScript::luaClearPlayerGuild);
	lua_register(luaState, "setPlayerGuildNick", NpcScript::luaSetPlayerGuildNick);
	lua_register(luaState, "setPlayerGuildTitle", NpcScript::luaSetPlayerGuildNick);	// old
#endif //YUR_GUILD_SYSTEM

#ifdef YUR_PREMIUM_PROMOTION
	lua_register(luaState, "isPremium", NpcScript::luaIsPremium);
	lua_register(luaState, "isPromoted", NpcScript::luaIsPromoted);
#endif //YUR_PREMIUM_PROMOTION

#ifdef YUR_ROOKGARD
	lua_register(luaState, "setPlayerVocation", NpcScript::luaSetPlayerVocation);
#endif //YUR_ROOKGARD

#ifdef YUR_LEARN_SPELLS
	lua_register(luaState, "learnSpell", NpcScript::luaLearnSpell);
#endif //YUR_LEARN_SPELLS

	return true;
}

Npc* NpcScript::getNpc(lua_State *L){
	lua_getglobal(L, "addressOfNpc");
	int val = (int)lua_tonumber(L, -1);
	lua_pop(L,1);
	Npc* mynpc = (Npc*)val;

	if(!mynpc){
		return 0;
	}
	return mynpc;
}

int NpcScript::luaCreatureGetName2(lua_State *L){
	const char* s = lua_tostring(L, -1);
	lua_pop(L,1);
	Npc* mynpc = getNpc(L);
	Creature *c = mynpc->game->getCreatureByName(std::string(s));

	if(c && c->access < g_config.ACCESS_PROTECT) {
		lua_pushnumber(L, c->getID());
	}
	else
		lua_pushnumber(L, 0);

	return 1;
}

int NpcScript::luaCreatureGetName(lua_State *L){
	int id = (int)lua_tonumber(L, -1);
	lua_pop(L,1);
	Npc* mynpc = getNpc(L);
	lua_pushstring(L, mynpc->game->getCreatureByID(id)->getName().c_str());
	return 1;
}

int NpcScript::luaCreatureGetPos(lua_State *L){
	int id = (int)lua_tonumber(L, -1);
	lua_pop(L,1);
	Npc* mynpc = getNpc(L);
	Creature* c = mynpc->game->getCreatureByID(id);

	if(!c){
		lua_pushnil(L);
		lua_pushnil(L);
		lua_pushnil(L);
	}
	else{
		lua_pushnumber(L, c->pos.x);
		lua_pushnumber(L, c->pos.y);
		lua_pushnumber(L, c->pos.z);
	}
	return 3;
}

int NpcScript::luaSelfGetPos(lua_State *L){
	lua_pop(L,1);
	Npc* mynpc = getNpc(L);
	lua_pushnumber(L, mynpc->pos.x);
	lua_pushnumber(L, mynpc->pos.y);
	lua_pushnumber(L, mynpc->pos.z);
	return 3;
}

int NpcScript::luaActionSay(lua_State* L){
	int len = (uint32_t)lua_strlen(L, -1);
	std::string msg(lua_tostring(L, -1), len);
	lua_pop(L,1);
	//now, we got the message, we now have to find out
	//what npc this belongs to

	Npc* mynpc=getNpc(L);
	if(mynpc)
		mynpc->doSay(msg);
	return 0;
}

int NpcScript::luaDoPlayerSendTextMessage(lua_State* L)
{
	const char* text = lua_tostring(L, -1);
	int messageClass = (int)lua_tonumber(L, -2);
	int cid = (int)lua_tonumber(L, -3);
	lua_pop(L, 3);

	Npc* mynpc = getNpc(L);
	if(!mynpc)
		return 0;

	Creature* creature = mynpc->game->getCreatureByID(cid);
	Player* player = creature ? dynamic_cast<Player*>(creature) : NULL;
	if(player)
		player->sendTextMessage((MessageClasses)messageClass, text);

	return 0;
}

int NpcScript::luaActionMove(lua_State* L){
	int dir=(int)lua_tonumber(L, -1);
	lua_pop(L,1);
	Npc* mynpc=getNpc(L);
	if(mynpc)
		mynpc->doMove(dir);
	return 0;
}

int NpcScript::luaActionMoveTo(lua_State* L){
	Position target;
	target.z=(int)lua_tonumber(L, -1);
	lua_pop(L,1);
	target.y=(int)lua_tonumber(L, -1);
	lua_pop(L,1);
	target.x=(int)lua_tonumber(L, -1);
	lua_pop(L,1);
	Npc* mynpc=getNpc(L);
	if(mynpc)
		mynpc->doMoveTo(target);
	return 0;
}



int NpcScript::luaActionAttackCreature(lua_State *L){
	int id=(int)lua_tonumber(L, -1);
	lua_pop(L,1);
	Npc* mynpc=getNpc(L);
	if(mynpc)
		mynpc->doAttack(id);
	return 0;
}


#ifdef TLM_BUY_SELL
int NpcScript::luaBuyItem(lua_State *L)
{
	int cost = (int)lua_tonumber(L, -1);
	int count = (int)lua_tonumber(L, -2);
	int itemid = (int)lua_tonumber(L, -3);
	int cid = (int)lua_tonumber(L, -4);
	lua_pop(L,4);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(cid);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if (player)
	{
		PendingTransaction& pt = preparePendingTrade(mynpc->getID());
		pt.cid = cid;
		pt.itemid = itemid;
		pt.count = count;
		pt.cost = cost;
		pt.isSell = false;

		std::stringstream ss;
		if(Item::items[itemid].isFluidContainer() && count != 0) {
			ss << "Buy 1 " << Item::getFluidTypeName(count) << " for " << cost << " gp? (yes or si)";
		} else {
			ss << "Buy " << count << "x " << Item::items[itemid].name << " for " << cost << " gp? (yes or si)";
		}
		mynpc->doSay(ss.str());
	}

	return 0;
}

int NpcScript::luaSellItem(lua_State *L)
{
   int cost = (int)lua_tonumber(L, -1);
   int count = (int)lua_tonumber(L, -2);
   int itemid = (int)lua_tonumber(L, -3);
   int cid = (int)lua_tonumber(L, -4);
   lua_pop(L,4);

   Npc* mynpc = getNpc(L);
   Creature* creature = mynpc->game->getCreatureByID(cid);
   Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if (player)
	{
		PendingTransaction& pt = preparePendingTrade(mynpc->getID());
		pt.cid = cid;
		pt.itemid = itemid;
		pt.count = count;
		pt.cost = cost;
		pt.isSell = true;

		std::stringstream ss;
		ss << "Sell " << count << "x " << Item::items[itemid].name << " for " << cost << " gp? (yes or si)";
		mynpc->doSay(ss.str());
	}

	return 0;
}

int NpcScript::luaSellBundle(lua_State *L)
{
	if(!lua_istable(L, -1))
		return 0;

	const char* label = lua_tostring(L, -2);
	int cost = (int)lua_tonumber(L, -3);
	int cid = (int)lua_tonumber(L, -4);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(cid);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if(player)
	{
		PendingTransaction& pt = preparePendingTrade(mynpc->getID());
		pt.cid = cid;
		pt.itemid = 0;
		pt.count = 0;
		pt.cost = cost;
		pt.isSell = true;
		pt.isBulkSell = true;
		pt.bulkItems.clear();
		pt.bulkLabel = label? label : "";

		lua_pushnil(L);
		while(lua_next(L, 4) != 0){
			if(lua_istable(L, -1)){
				lua_rawgeti(L, -1, 1);
				int itemid = (int)lua_tonumber(L, -1);
				lua_pop(L, 1);
				lua_rawgeti(L, -1, 2);
				int count = (int)lua_tonumber(L, -1);
				lua_pop(L, 1);
				if(itemid > 0 && count > 0)
					pt.bulkItems.push_back(std::make_pair(itemid, count));
			}
			lua_pop(L, 1);
		}

		std::stringstream ss;
		ss << "Sell " << pt.bulkLabel << " for " << cost << " gp? (yes or si)";
		mynpc->doSay(ss.str());
	}

	return 0;
}

int NpcScript::luaCancelPendingTrade(lua_State *L)
{
	int cid = 0;
	int top = lua_gettop(L);
	if(top >= 1)
		cid = (int)lua_tonumber(L, -1);
	lua_pop(L, top);

	Npc* mynpc = getNpc(L);
	if(!mynpc){
		lua_pushboolean(L, false);
		return 1;
	}

	lua_pushboolean(L, clearPendingTrade(mynpc->getID(), cid));
	return 1;
}

int NpcScript::luaPayMoney(lua_State *L)
{
   int cost = (int)lua_tonumber(L, -1);
   int cid = (int)lua_tonumber(L, -2);
   lua_pop(L,2);

   Npc* mynpc = getNpc(L);
   Creature* creature = mynpc->game->getCreatureByID(cid);
   Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if (player)
	{
		if (player->canPayWithBank((unsigned long)cost))
		{
			if (player->removeCoinsWithBank((unsigned long)cost))
				lua_pushboolean(L, true);
			else
				lua_pushboolean(L, false);
		}
		else
			lua_pushboolean(L, false);
	}
	else
		lua_pushboolean(L, false);

	return 1;
}
#endif //TLM_BUY_SELL


#ifdef YUR_NPC_EXT
int NpcScript::luaGetPlayerStorageValue(lua_State* L)
{
	int id = (int)lua_tonumber(L, -2);
	unsigned long key = (unsigned long)lua_tonumber(L, -1);
	lua_pop(L, 2);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(id);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	long value;
	if (player && player->getStorageValue(key, value))
		lua_pushnumber(L, value);
	else
		lua_pushnumber(L, -1);

	return 1;
}

int NpcScript::luaSetPlayerStorageValue(lua_State* L)
{
	int id = (int)lua_tonumber(L, -3);
	unsigned long key = (unsigned long)lua_tonumber(L, -2);
	long value = (long)lua_tonumber(L, -1);
	lua_pop(L, 3);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(id);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if (player)
		player->addStorageValue(key, value);

	return 0;
}

int NpcScript::luaPlayerRemoveItem(lua_State* L)
{
	int count = 1;
	if(lua_gettop(L) >= 3)
		count = (int)lua_tonumber(L, -1);

	int item_id = (int)lua_tonumber(L, -2);
	int id = (int)lua_tonumber(L, -3);
	lua_pop(L, 3);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(id);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if (player && player->removeItem(item_id, count))
		lua_pushnumber(L, 0);
	else
		lua_pushnumber(L, -1);

	return 1;
}

int NpcScript::luaPlayerAddItem(lua_State* L)
{
	int count = (int)lua_tonumber(L, -1);
	int itemid = (int)lua_tonumber(L, -2);
	int cid = (int)lua_tonumber(L, -3);
	lua_pop(L, 3);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(cid);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if(player){
		player->TLMaddItem(itemid, (unsigned char)count);
		lua_pushnumber(L, 0);
	}else
		lua_pushnumber(L, -1);

	return 1;
}

int NpcScript::luaGetPlayerLevel(lua_State* L)
{
	const char* name = lua_tostring(L, -1);
	lua_pop(L, 1);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByName(name);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if (player)
		lua_pushnumber(L, player->getLevel());
	else
		lua_pushnumber(L, -1);

	return 1;
}

int NpcScript::luaGetPlayerMoney(lua_State* L)
{
	int cid = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(cid);
	Player* player = creature ? dynamic_cast<Player*>(creature) : NULL;

	if(player)
		lua_pushnumber(L, player->getMoney());
	else
		lua_pushnumber(L, -1);

	return 1;
}

int NpcScript::luaGetPlayerBankBalance(lua_State* L)
{
	int cid = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(cid);
	Player* player = creature ? dynamic_cast<Player*>(creature) : NULL;

	if(!player) {
		lua_pushnumber(L, -1);
		return 1;
	}

	Account account;
	if(!loadAccountByNumber((unsigned long)player->getAccount(), account)) {
		lua_pushnumber(L, -1);
		return 1;
	}

	lua_pushnumber(L, (lua_Number)account.balance);
	return 1;
}

int NpcScript::luaDepositPlayerMoney(lua_State* L)
{
	int64_t amount = (int64_t)lua_tonumber(L, -1);
	int cid = (int)lua_tonumber(L, -2);
	lua_pop(L, 2);

	if(amount <= 0) {
		lua_pushnumber(L, BANK_ACTION_INVALID_AMOUNT);
		return 1;
	}

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(cid);
	Player* player = creature ? dynamic_cast<Player*>(creature) : NULL;
	if(!player) {
		lua_pushnumber(L, BANK_ACTION_PLAYER_NOT_FOUND);
		return 1;
	}

	Account account;
	if(!loadAccountByNumber((unsigned long)player->getAccount(), account)) {
		lua_pushnumber(L, BANK_ACTION_ACCOUNT_NOT_FOUND);
		return 1;
	}

	if(player->getMoney() < (unsigned long)amount || !player->substractMoney((unsigned long)amount)) {
		lua_pushnumber(L, BANK_ACTION_NOT_ENOUGH_MONEY);
		return 1;
	}

	if(!persistPlayerState(player)) {
		addMoneyToPlayer(player, (uint64_t)amount);
		persistPlayerState(player);
		lua_pushnumber(L, BANK_ACTION_SAVE_FAILED);
		return 1;
	}

	account.balance += (uint64_t)amount;
	if(!IOAccount::instance()->saveAccount(account)) {
		addMoneyToPlayer(player, (uint64_t)amount);
		persistPlayerState(player);
		lua_pushnumber(L, BANK_ACTION_SAVE_FAILED);
		return 1;
	}

	lua_pushnumber(L, BANK_ACTION_SUCCESS);
	return 1;
}

int NpcScript::luaWithdrawPlayerMoney(lua_State* L)
{
	int64_t amount = (int64_t)lua_tonumber(L, -1);
	int cid = (int)lua_tonumber(L, -2);
	lua_pop(L, 2);

	if(amount <= 0) {
		lua_pushnumber(L, BANK_ACTION_INVALID_AMOUNT);
		return 1;
	}

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(cid);
	Player* player = creature ? dynamic_cast<Player*>(creature) : NULL;
	if(!player) {
		lua_pushnumber(L, BANK_ACTION_PLAYER_NOT_FOUND);
		return 1;
	}

	Account account;
	if(!loadAccountByNumber((unsigned long)player->getAccount(), account)) {
		lua_pushnumber(L, BANK_ACTION_ACCOUNT_NOT_FOUND);
		return 1;
	}

	if(account.balance < (uint64_t)amount) {
		lua_pushnumber(L, BANK_ACTION_NOT_ENOUGH_BALANCE);
		return 1;
	}

	account.balance -= (uint64_t)amount;
	if(!IOAccount::instance()->saveAccount(account)) {
		lua_pushnumber(L, BANK_ACTION_SAVE_FAILED);
		return 1;
	}

	addMoneyToPlayer(player, (uint64_t)amount);
	if(!persistPlayerState(player)) {
		player->substractMoney((unsigned long)amount);
		account.balance += (uint64_t)amount;
		IOAccount::instance()->saveAccount(account);
		persistPlayerState(player);
		lua_pushnumber(L, BANK_ACTION_SAVE_FAILED);
		return 1;
	}

	lua_pushnumber(L, BANK_ACTION_SUCCESS);
	return 1;
}

int NpcScript::luaTransferPlayerMoneyTo(lua_State* L)
{
	const char* target = lua_tostring(L, -1);
	int64_t amount = (int64_t)lua_tonumber(L, -2);
	int cid = (int)lua_tonumber(L, -3);
	lua_pop(L, 3);

	if(amount <= 0) {
		lua_pushnumber(L, BANK_ACTION_INVALID_AMOUNT);
		return 1;
	}

	if(!target || target[0] == '\0') {
		lua_pushnumber(L, BANK_ACTION_TARGET_NOT_FOUND);
		return 1;
	}

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(cid);
	Player* player = creature ? dynamic_cast<Player*>(creature) : NULL;
	if(!player) {
		lua_pushnumber(L, BANK_ACTION_PLAYER_NOT_FOUND);
		return 1;
	}

	Account sourceAccount;
	if(!loadAccountByNumber((unsigned long)player->getAccount(), sourceAccount)) {
		lua_pushnumber(L, BANK_ACTION_ACCOUNT_NOT_FOUND);
		return 1;
	}

	if(sourceAccount.balance < (uint64_t)amount) {
		lua_pushnumber(L, BANK_ACTION_NOT_ENOUGH_BALANCE);
		return 1;
	}

	Account targetAccount;
	if(!resolvePlayerAccountByName(target, targetAccount)) {
		lua_pushnumber(L, BANK_ACTION_TARGET_NOT_FOUND);
		return 1;
	}

	if(targetAccount.accnumber == sourceAccount.accnumber) {
		lua_pushnumber(L, BANK_ACTION_SAME_ACCOUNT);
		return 1;
	}

	sourceAccount.balance -= (uint64_t)amount;
	targetAccount.balance += (uint64_t)amount;

	if(!IOAccount::instance()->saveAccount(sourceAccount)) {
		lua_pushnumber(L, BANK_ACTION_SAVE_FAILED);
		return 1;
	}

	if(!IOAccount::instance()->saveAccount(targetAccount)) {
		sourceAccount.balance += (uint64_t)amount;
		IOAccount::instance()->saveAccount(sourceAccount);
		lua_pushnumber(L, BANK_ACTION_SAVE_FAILED);
		return 1;
	}

	lua_pushnumber(L, BANK_ACTION_SUCCESS);
	return 1;
}

int NpcScript::luaGetPlayerItemCount(lua_State* L)
{
	int itemid = (int)lua_tonumber(L, -1);
	int cid = (int)lua_tonumber(L, -2);
	lua_pop(L, 2);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(cid);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if(player)
		lua_pushnumber(L, player->getItemCount(itemid));
	else
		lua_pushnumber(L, 0);

	return 1;
}

int NpcScript::luaSetPlayerMasterPos(lua_State* L)
{
	int id = (int)lua_tonumber(L, -4);
	int x = (int)lua_tonumber(L, -3);
	int y = (int)lua_tonumber(L, -2);
	int z = (int)lua_tonumber(L, -1);
	lua_pop(L, 4);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(id);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if (player)
	{
		Position pos(x,y,z);
		Tile* tile = mynpc->game->getTile(pos);

		if (tile)
			player->masterPos = pos;
		else
			std::cout << "NpcScript: luaSetPlayerMasterPos: given position is invalid!" << std::endl;
	}

	return 0;
}
#endif //YUR_NPC_EXT


#ifdef YUR_GUILD_SYSTEM
int NpcScript::luaFoundNewGuild(lua_State* L)
{
	const char* gname = lua_tostring(L, -1);
	lua_pop(L, 1);

	if (gname)
		lua_pushnumber(L, Guilds::AddNewGuild(gname));
	else
		lua_pushnumber(L, -1);

	return 1;
}

int NpcScript::luaGetPlayerGuildStatus(lua_State* L)
{
	const char* name = lua_tostring(L, -1);
	lua_pop(L, 1);
	lua_pushnumber(L, Guilds::GetGuildStatus(name));
	return 1;
}

int NpcScript::luaSetPlayerGuildStatus(lua_State* L)
{
	const char* name = lua_tostring(L, -2);
	int gstat = (int)lua_tonumber(L, -1);
	lua_pop(L, 2);

	Guilds::SetGuildStatus(std::string(name), (gstat_t)gstat);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByName(name);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if (player)
		Guilds::ReloadGuildInfo(player);

	return 0;
}

int NpcScript::luaGetPlayerGuildName(lua_State* L)
{
	const char* name = lua_tostring(L, -1);
	lua_pop(L, 1);
	lua_pushstring(L, Guilds::GetGuildName(name).c_str());
	return 1;
}

int NpcScript::luaSetPlayerGuild(lua_State* L)
{
	const char* name = lua_tostring(L, -4);
	int gstat = (int)lua_tonumber(L, -3);
	const char* grank = lua_tostring(L, -2);
	const char* gname = lua_tostring(L, -1);
	lua_pop(L, 4);

	Guilds::SetGuildInfo(name, (gstat_t)gstat, grank, gname);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByName(name);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if (player)
		Guilds::ReloadGuildInfo(player);

	return 0;
}

int NpcScript::luaClearPlayerGuild(lua_State* L)
{
	const char* name = lua_tostring(L, -1);
	lua_pop(L, 1);

	Guilds::ClearGuildInfo(name);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByName(name);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if (player)
		Guilds::ReloadGuildInfo(player);

	return 0;
}

int NpcScript::luaSetPlayerGuildNick(lua_State* L)
{
	const char* name = lua_tostring(L, -2);
	const char* nick = lua_tostring(L, -1);
	lua_pop(L, 2);

	Guilds::SetGuildNick(name, nick);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByName(name);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if (player)
		Guilds::ReloadGuildInfo(player);

	return 0;
}
#endif //YUR_GUILD_SYSTEM


#ifdef YUR_ROOKGARD
int NpcScript::luaSetPlayerVocation(lua_State* L)
{
	int id = (int)lua_tonumber(L, -2);
	int voc = (int)lua_tonumber(L, -1);
	lua_pop(L, 2);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(id);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if (player)
		player->setVocation((playervoc_t)voc);

	return 0;
}
#endif //YUR_ROOKGARD


#ifdef YUR_LEARN_SPELLS
int NpcScript::luaGetPlayerVocation(lua_State* L)
{
	int id = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(id);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if (player)
		lua_pushnumber(L, player->getVocation());
	else
		lua_pushnumber(L, -1);

	return 1;
}

int NpcScript::luaLearnSpell(lua_State *L)
{
	int cid = (int)lua_tonumber(L, -3);
	const char* words = lua_tostring(L, -2);
	int cost = (int)lua_tonumber(L, -1);
	lua_pop(L,3);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(cid);
	Player *player = creature? dynamic_cast<Player*>(creature) : NULL;

	if (player)
	{
		if (player->knowsSpell(words))
		{
			mynpc->doSay("You already know this spell.");
		}
		else if (player->canPayWithBank((unsigned long)cost))
		{
			if (player->removeCoinsWithBank((unsigned long)cost))
			{
				player->learnSpell(words);
				player->sendMagicEffect(player->pos, NM_ME_MAGIC_ENERGIE);
				mynpc->doSay((std::string("To use it say: ") + std::string(words) + ".").c_str());
			}
			else
				mynpc->doSay("Sorry, you do not have enough money.");
		}
		else
			mynpc->doSay("Sorry, you do not have enough money.");
	}

	return 0;
}
#endif //YUR_LEARN_SPELLS


#ifdef YUR_PREMIUM_PROMOTION
int NpcScript::luaIsPromoted(lua_State* L)
{
	int id = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(id);
	Player* player = creature? dynamic_cast<Player*>(creature) : NULL;

	if (player)
		lua_pushboolean(L, player->isPromoted());
	else
		lua_pushboolean(L, false);

	return 1;
}

int NpcScript::luaIsPremium(lua_State* L)
{
	int id = (int)lua_tonumber(L, -1);
	lua_pop(L, 1);

	Npc* mynpc = getNpc(L);
	Creature* creature = mynpc->game->getCreatureByID(id);
	Player* player = dynamic_cast<Player*>(creature);

	if (player)
		lua_pushboolean(L, player->isPremium());
	else
		lua_pushboolean(L, false);

	return 1;
}
#endif //YUR_PREMIUM_PROMOTION
