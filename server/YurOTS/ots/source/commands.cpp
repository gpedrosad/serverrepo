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

#include <string>
#include <sstream>
#include <fstream>
#include <utility>
#include <vector>
#include <algorithm>

#include "commands.h"
#include "houses.h"
#include "monster.h"
#include "player.h"
#include "npc.h"
#include "game.h"
#include "actions.h"
#include "map.h"
#include "status.h"
#include "monsters.h"
#include "spells.h"
#include "ioplayer.h"
#include <libxml/xmlmemory.h>
#include <libxml/parser.h>

extern std::vector< std::pair<unsigned long, unsigned long> > bannedIPs;
extern Actions actions;
extern Monsters g_monsters;
extern Spells spells;

extern bool readXMLInteger(xmlNodePtr p, const char *tag, int &value);

// Ayudas de los comandos de GM (docs/gameplay/GM_COMANDOS.md)
namespace {

std::string gmTrim(const std::string& s)
{
	std::string::size_type a = s.find_first_not_of(" \t");
	if(a == std::string::npos)
		return "";
	std::string::size_type b = s.find_last_not_of(" \t");
	return s.substr(a, b - a + 1);
}

bool gmIsNumber(const std::string& s)
{
	if(s.empty())
		return false;
	for(std::string::size_type i = 0; i < s.size(); ++i)
		if(s[i] < '0' || s[i] > '9')
			return false;
	return true;
}

// "texto 25" -> text="texto", number=25. Sin numero al final: number = defaultNumber.
void gmSplitTrailingNumber(const std::string& param, std::string& text, long& number, long defaultNumber)
{
	std::string p = gmTrim(param);
	number = defaultNumber;
	std::string::size_type sp = p.find_last_of(' ');
	if(sp != std::string::npos && gmIsNumber(p.substr(sp + 1))) {
		number = atol(p.substr(sp + 1).c_str());
		text = gmTrim(p.substr(0, sp));
	}
	else
		text = p;
}

// "25 nombre del jugador" -> number=25, rest="nombre del jugador". false si no empieza con numero.
bool gmSplitLeadingNumber(const std::string& param, long& number, std::string& rest)
{
	std::string p = gmTrim(param);
	std::string::size_type sp = p.find(' ');
	std::string first = (sp == std::string::npos) ? p : p.substr(0, sp);
	if(!gmIsNumber(first))
		return false;
	number = atol(first.c_str());
	rest = (sp == std::string::npos) ? "" : gmTrim(p.substr(sp + 1));
	return true;
}

std::string gmLower(std::string s)
{
	std::transform(s.begin(), s.end(), s.begin(), tolower);
	return s;
}

long gmClamp(long v, long lo, long hi)
{
	return v < lo ? lo : (v > hi ? hi : v);
}

void gmInfo(Player* player, const std::string& msg)
{
	if(player)
		player->sendTextMessage(MSG_BLUE_TEXT, msg.c_str());
}

bool gmFreeTile(Tile* tile)
{
	return tile && tile->isBlocking(BLOCK_SOLID, true) == RET_NOERROR;
}

struct GmLootCount {
	long drops;
	long total;
	GmLootCount() : drops(0), total(0) {}
};

void gmCountLoot(Container* container, std::map<unsigned short, GmLootCount>& counts)
{
	for(ContainerList::const_iterator it = container->getItems(); it != container->getEnd(); ++it) {
		Item* item = *it;
		if(!item)
			continue;
		GmLootCount& c = counts[item->getID()];
		c.drops++;
		c.total += item->isStackable() ? item->getItemCountOrSubtype() : 1;
		if(Container* sub = dynamic_cast<Container*>(item))
			gmCountLoot(sub, counts);
	}
}

bool gmLootSort(const std::pair<unsigned short, GmLootCount>& a, const std::pair<unsigned short, GmLootCount>& b)
{
	return a.second.drops > b.second.drops;
}

} // namespace

//table of commands
s_defcommands Commands::defined_commands[] = {
	{"/s",&Commands::placeNpc},
	{"/m",&Commands::placeMonster},
	{"/summon",&Commands::placeSummon},
	{"/B",&Commands::broadcastMessage},
	{"/b",&Commands::banPlayer},
	{"/t",&Commands::teleportMasterPos},
	{"/c",&Commands::teleportHere},
	{"/i",&Commands::createItems},
	{"/q",&Commands::substract_contMoney},
	{"/reload",&Commands::reloadInfo},
	{"/z",&Commands::testCommand},
	{"/goto",&Commands::teleportTo},
	{"/info",&Commands::getInfo},
	{"/closeserver",&Commands::closeServer},
	{"/openserver",&Commands::openServer},
	{"/getonline",&Commands::onlineList},
	{"/ips",&Commands::onlineIpList},
	{"/a",&Commands::teleportNTiles},
	{"/kick",&Commands::kickPlayer},
	{"/pink",&Commands::pinkSkull},
	{"/unpink",&Commands::unpinkSkull},
	{"/ban",&Commands::banCharacter},
	{"/up",&Commands::goUp},
	{"/down",&Commands::goDown},
	{"/pos",&Commands::showPos},
	{"/pvp",&Commands::setWorldType},
	{"/send",&Commands::teleportPlayerTo},
	{"/max",&Commands::setMaxPlayers},
	{"!exp",&Commands::showExpForLvl},
	{"!mana",&Commands::showManaForLvl},
	{"!report",&Commands::report},
	{"!online",&Commands::whoIsOnline},
	{"!uptime",&Commands::showUptime},
	{"!pz",&Commands::showPz},
	{"/owner",&Commands::setHouseOwner},
	{"!house",&Commands::reloadRights},
	{"!buyhouse",&Commands::buyHouse},
	{"!leavehouse",&Commands::leaveHouse},
	{"/invisible",&Commands::gmInvisible},
	{"!frags",&Commands::showFrags},
	{"/save",&Commands::forceServerSave},
	{"/shutdown",&Commands::shutdown},
	{"/clean",&Commands::cleanMap},
	{"/promote",&Commands::promote},
	{"!premmy",&Commands::showPremmy},
	{"/god",&Commands::gmGod},
	{"/ir",&Commands::gmGoPlace},
	{"/nivel",&Commands::gmSetLevel},
	{"/skill",&Commands::gmSetSkill},
	{"/ml",&Commands::gmSetMagicLevel},
	{"/loot",&Commands::gmLootTest},
	{"/matar",&Commands::gmKillMonsters},
	{"/speed",&Commands::gmSpeed},
	{"/comandos",&Commands::gmHelp},
};

Commands::Commands(Game* igame):
game(igame),
loaded(false)
{
	//setup command map
	for(int i = 0;i< sizeof(defined_commands)/sizeof(defined_commands[0]); i++){
		Command *tmp = new Command;
		tmp->loaded = false;
		tmp->accesslevel = 1;
		tmp->f = defined_commands[i].f;
		std::string key = defined_commands[i].name;
		commandMap[key] = tmp;
	}
}

bool Commands::loadXml(const std::string &_datadir){

	datadir = _datadir;

	std::string filename = datadir + "commands.xml";
	std::transform(filename.begin(), filename.end(), filename.begin(), tolower);
	xmlDocPtr doc = xmlParseFile(filename.c_str());

	if (doc){
		this->loaded = true;
		xmlNodePtr root, p;
		root = xmlDocGetRootElement(doc);

		if (xmlStrcmp(root->name,(const xmlChar*) "commands")){
			xmlFreeDoc(doc);
			return false;
		}
		p = root->children;

		while (p)
		{
			const char* str = (char*)p->name;

			if (strcmp(str, "command") == 0){
				char *tmp = (char*)xmlGetProp(p, (const xmlChar *) "cmd");
				if(tmp){
					CommandMap::iterator it = commandMap.find(tmp);
					int alevel;
					if(it != commandMap.end()){
						if(readXMLInteger(p,"access",alevel)){
							if(!it->second->loaded){
								it->second->accesslevel = alevel;
								it->second->loaded = true;
							}
							else{
								std::cout << "Duplicated command " << tmp << std::endl;
							}
						}
						else{
							std::cout << "missing access tag for " << tmp << std::endl;
						}
					}
					else{
						//error
						std::cout << "Unknown command " << tmp << std::endl;
					}
					xmlFreeOTSERV(tmp);
				}
				else{
					std::cout << "missing cmd." << std::endl;
				}
			}
			p = p->next;
		}
		xmlFreeDoc(doc);
	}

	//
	for(CommandMap::iterator it = commandMap.begin(); it != commandMap.end(); ++it){
		if(it->second->loaded == false){
			std::cout << "Warning: Missing access level for command" << it->first << std::endl;
		}
		//register command tag in game
		game->addCommandTag(it->first.substr(0,1));
	}

	return this->loaded;
}

bool Commands::reload(){
	this->loaded = false;
	for(CommandMap::iterator it = commandMap.begin(); it != commandMap.end(); ++it){
		it->second->accesslevel = 1;
		it->second->loaded = false;
	}
	game->resetCommandTag();
	this->loadXml(datadir);
	return true;
}

bool Commands::exeCommand(Creature *creature, const std::string &cmd){

	std::string str_command;
	std::string str_param;

	unsigned int loc = (uint32_t)cmd.find( ' ', 0 );
	if( loc != std::string::npos && loc >= 0){
		str_command = std::string(cmd, 0, loc);
		str_param = std::string(cmd, (loc+1), cmd.size()-loc-1);
	}
	else {
		str_command = cmd;
		str_param = std::string("");
	}

	//find command
	CommandMap::iterator it = commandMap.find(str_command);
	if(it == commandMap.end()){
		return false;
	}
	Player *player = dynamic_cast<Player*>(creature);
	//check access for this command
	if(creature->access < it->second->accesslevel){
		if(creature->access > 0){
			if (player)
				player->sendTextMessage(MSG_SMALLINFO,"You cannot execute this command.");
			else
				std::cout << "WARNING: " << creature->getName() << " does not have access to execute " << cmd << '!' << std::endl;
			return true;
		}
		else{
			return false;
		}
	}
	//execute command
	CommandFunc cfunc = it->second->f;
	(this->*cfunc)(creature, str_command, str_param);
	if(player)
		player->sendTextMessage(MSG_RED_TEXT,cmd.c_str());

	return true;
}

bool Commands::placeNpc(Creature* c, const std::string &cmd, const std::string &param)
{
	Npc *npc = new Npc(param, game);
	if(!npc->isLoaded()){
		delete npc;
		return true;
	}
	Position pos;
	// Set the NPC pos
	if(c->direction == NORTH) {
		pos.x = c->pos.x;
		pos.y = c->pos.y - 1;
		pos.z = c->pos.z;
	}
	// South
	if(c->direction == SOUTH) {
		pos.x = c->pos.x;
		pos.y = c->pos.y + 1;
		pos.z = c->pos.z;
	}
	// East
	if(c->direction == EAST) {
		pos.x = c->pos.x + 1;
		pos.y = c->pos.y;
		pos.z = c->pos.z;
	}
	// West
	if(c->direction == WEST) {
		pos.x = c->pos.x - 1;
		pos.y = c->pos.y;
		pos.z = c->pos.z;
	}
	// Place the npc
	if(!game->placeCreature(pos, npc))
	{
		delete npc;
		Player *player = dynamic_cast<Player*>(c);
		if(player) {
			player->sendMagicEffect(player->pos, NM_ME_PUFF);
			player->sendCancel("Sorry not enough room.");
		}
		return true;
	}
	return true;
}

bool Commands::placeMonster(Creature* c, const std::string &cmd, const std::string &param)
{

	Monster* monster = Monster::createMonster(param, game);

	if(!monster){
		//delete monster;
		return true;
	}
	Position pos;

	// Set the Monster pos
	if(c->direction == NORTH) {
		pos.x = c->pos.x;
		pos.y = c->pos.y - 1;
		pos.z = c->pos.z;
	}
	// South
	if(c->direction == SOUTH) {
		pos.x = c->pos.x;
		pos.y = c->pos.y + 1;
		pos.z = c->pos.z;
	}
	// East
	if(c->direction == EAST) {
		pos.x = c->pos.x + 1;
		pos.y = c->pos.y;
		pos.z = c->pos.z;
	}
	// West
	if(c->direction == WEST) {
		pos.x = c->pos.x - 1;
		pos.y = c->pos.y;
		pos.z = c->pos.z;
	}

	// Place the monster
	if(!game->placeCreature(pos, monster)) {
		delete monster;
		Player *player = dynamic_cast<Player*>(c);
		if(player) {
			player->sendMagicEffect(player->pos, NM_ME_PUFF);
			player->sendCancel("Sorry, not enough room.");
		}
		return true;
	}
	else{

		return true;
	}
}

bool Commands::placeSummon(Creature* c, const std::string &cmd, const std::string &param)
{

	Monster* monster = Monster::createMonster(param, game);

	if(!monster){
		//delete monster;
		return true;
	}
	Position pos;

	// Set the Monster pos
	if(c->direction == NORTH) {
		pos.x = c->pos.x;
		pos.y = c->pos.y - 1;
		pos.z = c->pos.z;
	}
	// South
	if(c->direction == SOUTH) {
		pos.x = c->pos.x;
		pos.y = c->pos.y + 1;
		pos.z = c->pos.z;
	}
	// East
	if(c->direction == EAST) {
		pos.x = c->pos.x + 1;
		pos.y = c->pos.y;
		pos.z = c->pos.z;
	}
	// West
	if(c->direction == WEST) {
		pos.x = c->pos.x - 1;
		pos.y = c->pos.y;
		pos.z = c->pos.z;
	}

	// Place the monster
	if(!game->placeCreature(pos, monster)) {
		delete monster;
		Player *player = dynamic_cast<Player*>(c);
		if(player) {
			player->sendMagicEffect(player->pos, NM_ME_PUFF);
			player->sendCancel("Sorry, not enough room.");
		}
		return true;
	}
	else{
		c->addSummon(monster);
		return true;
	}
}

bool Commands::broadcastMessage(Creature* c, const std::string &cmd, const std::string &param){
	game->creatureBroadcastMessage(c,param);
	return true;
}

bool Commands::banPlayer(Creature* c, const std::string &cmd, const std::string &param){

	Player* playerBan = game->getPlayerByName(param);
	if(playerBan) {

		Player* player = dynamic_cast<Player*>(c);
		if(player && player->access <= playerBan->access){
			player->sendTextMessage(MSG_BLUE_TEXT,"You cannot ban this player.");
			return true;
		}

		playerBan->sendTextMessage(MSG_RED_TEXT,"You have been banned.");
		std::pair<unsigned long, unsigned long> IpNetMask;
		IpNetMask.first = playerBan->lastip;
		IpNetMask.second = 0xFFFFFFFF;
		if(IpNetMask.first > 0) {
			bannedIPs.push_back(IpNetMask);
		}
		playerBan->kickPlayer();
		return true;
	}

	return false;
}

bool Commands::teleportMasterPos(Creature* c, const std::string &cmd, const std::string &param){
	game->teleport(c, c->masterPos);
	return true;
}

bool Commands::teleportHere(Creature* c, const std::string &cmd, const std::string &param){
	Creature* creature = game->getCreatureByName(param);
	if(creature) {
		game->teleport(creature, c->pos);
	}
	return true;
}

bool Commands::createItems(Creature* c, const std::string &cmd, const std::string &param){

	// /i 2160 5, /i 2160, /i black fire sword, /i platinum coin 50 (docs/gameplay/GM_COMANDOS.md)
	Player* self = dynamic_cast<Player*>(c);
	std::string what;
	long count;
	gmSplitTrailingNumber(param, what, count, -1);

	int type = gmIsNumber(what) ? atoi(what.c_str()) : Item::items.getIdByName(what);
	if(type <= 0 || Item::items[type].id == 0) {
		gmInfo(self, "No existe el item: " + what + ".");
		return true;
	}
	if(count < 0)   // sin cantidad: 1 si se apila, 10 cargas si es runa, si no nada
		count = Item::items[type].stackable ? 1 : (Item::items[type].runeMagLevel != -1 ? 10 : 0);
	count = std::min(count, 100L);

	Item *newItem = Item::CreateItem(type, (unsigned short)count);
	if(!newItem)
		return true;

	std::stringstream created;
	created << "Creado: " << Item::items[type].name << " (" << type << ")";
	if(Item::items[type].stackable || Item::items[type].runeMagLevel != -1)
		created << " x" << count;
	gmInfo(self, created.str() + ".");

	Tile *t = game->map->getTile(c->pos);
	if(!t)
	{
		delete newItem;
		return true;
	}

	game->addThing(NULL,c->pos,newItem);
	return true;

}

bool Commands::substract_contMoney(Creature* c, const std::string &cmd, const std::string &param){

	Player *player = dynamic_cast<Player *>(c);
	if(!player)
		return true;

	int count = atoi(param.c_str());
	unsigned long money = player->getMoney();
	if(!count)
	{
		std::stringstream info;
		info << "You have " << money << " of money.";
		player->sendCancel(info.str().c_str());
		return true;
	}
	else if(count > (int)money)
	{
		std::stringstream info;
		info << "You have " << money << " of money and is not suficient.";
		player->sendCancel(info.str().c_str());
		return true;
	}
	if(player->substractMoney(count) != true){
		std::stringstream info;
		info << "Can not substract money!";
		player->sendCancel(info.str().c_str());
	}
	return true;
}

bool Commands::reloadInfo(Creature* c, const std::string &cmd, const std::string &param)
{
	if(param == "actions"){
		actions.reload();
	}
	else if(param == "commands"){
		this->reload();
	}
	else if(param == "monsters"){
		g_monsters.reload();
	}
	else if(param=="spells"){
        spells.loadFromXml(g_config.getGlobalString("datadir"));
	}
	else if(param == "config"){
		g_config.OpenFile("config.lua");
	}
	else{
		Player *player = dynamic_cast<Player*>(c);
		if(player)
			player->sendCancel("Option not found.");
	}

	return true;
}

bool Commands::testCommand(Creature* c, const std::string &cmd, const std::string &param)
{
	int color = atoi(param.c_str());
	Player *player = dynamic_cast<Player*>(c);
	if(player) {
		player->sendMagicEffect(player->pos, color);
	}

	return true;
}

bool Commands::teleportTo(Creature* c, const std::string &cmd, const std::string &param){
	Creature* creature = game->getCreatureByName(param);
	if(creature) {
		Position pos = creature->pos;
		pos.x++; pos.y++;
		game->teleport(c, pos);
	}
	else	// teleport to position
	{
		std::istringstream in(param.c_str());
		Position pos;
		in >> pos.x >> pos.y >> pos.z;

		if (in)
			game->teleport(c, pos);
	}
	return true;
}

bool Commands::getInfo(Creature* c, const std::string &cmd, const std::string &param){
	Player *player = dynamic_cast<Player*>(c);
	if(!player)
		return true;

	Player* paramPlayer = game->getPlayerByName(param);
	if(paramPlayer) {
		std::stringstream info;
		unsigned char ip[4];
		if(paramPlayer->access >= player->access && player != paramPlayer){
			player->sendTextMessage(MSG_BLUE_TEXT,"You can not get info about this player.");
			return true;
		}
		*(unsigned long*)&ip = paramPlayer->lastip;
		info << "name:   " << paramPlayer->getName() << std::endl <<
		        "access: " << paramPlayer->access << std::endl <<
		        "level:  " << paramPlayer->getPlayerInfo(PLAYERINFO_LEVEL) << std::endl <<
		        "maglvl: " << paramPlayer->getPlayerInfo(PLAYERINFO_MAGICLEVEL) << std::endl <<
		        "speed:  " <<  paramPlayer->speed <<std::endl <<
		        "position " << paramPlayer->pos << std::endl <<
				"ip: " << (unsigned int)ip[0] << "." << (unsigned int)ip[1] <<
				   "." << (unsigned int)ip[2] << "." << (unsigned int)ip[3];
		player->sendTextMessage(MSG_BLUE_TEXT,info.str().c_str());
	}
	else{
		player->sendTextMessage(MSG_BLUE_TEXT,"Player not found.");
	}

	return true;
}

bool Commands::closeServer(Creature* c, const std::string &cmd, const std::string &param)
{
	game->setGameState(GAME_STATE_CLOSED);
	//kick players with access = 0
	AutoList<Player>::listiterator it = Player::listPlayer.list.begin();
	while(it != Player::listPlayer.list.end())
	{
		if((*it).second->access == 0){
			(*it).second->kickPlayer();
			it = Player::listPlayer.list.begin();
		}
		else{
			++it;
		}
	}

	return true;
}

bool Commands::openServer(Creature* c, const std::string &cmd, const std::string &param)
{
	game->setGameState(GAME_STATE_NORMAL);
	return true;
}

bool Commands::onlineList(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);
	unsigned long alevelmin = 0;
	unsigned long alevelmax = 10000;
	int i,n;
	if(!player)
		return false;

	if(param == "gm")
		alevelmin = 1;
	else if(param == "normal")
		alevelmax = 0;

	std::stringstream players;
	players << "name   level   mag" << std::endl;

	i = 0;
	n = 0;
	AutoList<Player>::listiterator it = Player::listPlayer.list.begin();
	for(;it != Player::listPlayer.list.end();++it)
	{
		if((*it).second->access >= (int)alevelmin && (*it).second->access <= (int)alevelmax){
			players << (*it).second->getName() << "   " <<
				(*it).second->getPlayerInfo(PLAYERINFO_LEVEL) << "    " <<
				(*it).second->getPlayerInfo(PLAYERINFO_MAGICLEVEL) << std::endl;
			n++;
			i++;
		}
		if(i == 10){
			player->sendTextMessage(MSG_BLUE_TEXT,players.str().c_str());
			players.str("");
			i = 0;
		}
	}
	if(i != 0)
		player->sendTextMessage(MSG_BLUE_TEXT,players.str().c_str());

	players.str("");
	players << "Total: " << n << " player(s)" << std::endl;
	player->sendTextMessage(MSG_BLUE_TEXT,players.str().c_str());
	return true;
}

namespace {
std::string formatIp(unsigned long ipValue)
{
	unsigned char ip[4];
	*(unsigned long*)&ip = ipValue;
	std::ostringstream os;
	os << (unsigned int)ip[0] << "." << (unsigned int)ip[1] << "."
	   << (unsigned int)ip[2] << "." << (unsigned int)ip[3];
	return os.str();
}

struct OnlineIpEntry {
	unsigned long ip;
	std::string name;
	int level;
};
} // namespace

bool Commands::onlineIpList(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);
	if(!player)
		return false;

	std::vector<OnlineIpEntry> entries;
	AutoList<Player>::listiterator it = Player::listPlayer.list.begin();
	for(; it != Player::listPlayer.list.end(); ++it) {
		Player* onlinePlayer = (*it).second;
		if(onlinePlayer->access >= player->access && onlinePlayer != player)
			continue;

		OnlineIpEntry entry;
		entry.ip = onlinePlayer->getIP();
		entry.name = onlinePlayer->getName();
		entry.level = onlinePlayer->getPlayerInfo(PLAYERINFO_LEVEL);
		entries.push_back(entry);
	}

	std::sort(entries.begin(), entries.end(),
		[](const OnlineIpEntry& a, const OnlineIpEntry& b) {
			if(a.ip != b.ip)
				return a.ip > b.ip;
			return a.name < b.name;
		});

	player->sendTextMessage(MSG_BLUE_TEXT, "Players online (by IP, desc):");
	player->sendTextMessage(MSG_BLUE_TEXT, "ip   name   lvl");

	std::stringstream chunk;
	int lines = 0;
	for(size_t i = 0; i < entries.size(); ++i) {
		const OnlineIpEntry& entry = entries[i];
		chunk << formatIp(entry.ip) << "   " << entry.name << "   "
		      << entry.level << std::endl;
		++lines;

		if(lines == 10) {
			player->sendTextMessage(MSG_BLUE_TEXT, chunk.str().c_str());
			chunk.str("");
			lines = 0;
		}
	}

	if(lines != 0)
		player->sendTextMessage(MSG_BLUE_TEXT, chunk.str().c_str());

	std::stringstream total;
	total << "Total: " << entries.size() << " player(s)";
	player->sendTextMessage(MSG_BLUE_TEXT, total.str().c_str());
	return true;
}

bool Commands::teleportNTiles(Creature* c, const std::string &cmd, const std::string &param){

	int ntiles = atoi(param.c_str());
	if(ntiles != 0)
	{
		Position new_pos;
		new_pos = c->pos;
		switch(c->direction){
		case NORTH:
			new_pos.y = new_pos.y - ntiles;
			break;
		case SOUTH:
			new_pos.y = new_pos.y + ntiles;
			break;
		case EAST:
			new_pos.x = new_pos.x + ntiles;
			break;
		case WEST:
			new_pos.x = new_pos.x - ntiles;
			break;
		}
		game->teleport(c, new_pos);
	}
	return true;
}

bool Commands::kickPlayer(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* playerKick = game->getPlayerByName(param);
	if(playerKick){
		Player* player = dynamic_cast<Player*>(c);
		if(player && player->access <= playerKick->access){
			player->sendTextMessage(MSG_BLUE_TEXT,"You cannot kick this player.");
			return true;
		}
		playerKick->kickPlayer();
		return true;
	}
	return false;
}

// ---------- Pink Skull (docs/gameplay/PINK_SKULL.md) ----------
// /pink Nombre            -> rosa hasta /unpink
// /pink "Nombre", horas   -> rosa por esas horas (1 a 500: skullTicks es int en ms)
// Solo jugadores conectados. Un GM no puede pon√©rsela a otro de su access o m√°s, salvo a s√≠ mismo
// (para probarla). Se guarda el personaje al momento, as√≠ sobrevive a un reinicio.
static std::string pinkTrim(std::string s)
{
	while(!s.empty() && (s[0] == ' ' || s[0] == '"'))
		s.erase(0, 1);
	while(!s.empty() && (s[s.size() - 1] == ' ' || s[s.size() - 1] == '"'))
		s.erase(s.size() - 1);
	return s;
}

static Player* pinkTarget(Game* game, Creature* c, const std::string& name, const char* verb)
{
	Player* gm = dynamic_cast<Player*>(c);
	Player* target = game->getPlayerByName(name);
	if(!target) {
		if(gm)
			gm->sendTextMessage(MSG_BLUE_TEXT, (std::string("Player ") + name + " is not online.").c_str());
		return NULL;
	}
	if(gm && target != gm && gm->access <= target->access) {
		gm->sendTextMessage(MSG_BLUE_TEXT, (std::string("You cannot ") + verb + " this player.").c_str());
		return NULL;
	}
	return target;
}

bool Commands::pinkSkull(Creature* c, const std::string &cmd, const std::string &param)
{
	std::string name = param;
	int hours = 0;
	size_t comma = param.rfind(',');
	if(comma != std::string::npos) {
		name = param.substr(0, comma);
		hours = atoi(param.substr(comma + 1).c_str());
		if(hours < 1 || hours > 500) {
			c->sendCancel("Use /pink \"Name\", hours (1-500), or /pink Name to keep it until /unpink.");
			return true;
		}
	}
	name = pinkTrim(name);
	Player* target = pinkTarget(game, c, name, "mark");
	if(!target)
		return true;

	target->skullType = SKULL_PINK;
	target->skullTicks = hours * 3600 * 1000;      // 0 = hasta /unpink (checkSkull solo descuenta si > 0)
	game->Skull(target);
	IOPlayer::instance()->savePlayer(target);

	std::stringstream msg;
	msg << target->getName() << " now has a pink skull";
	if(hours > 0)
		msg << " for " << hours << (hours == 1 ? " hour." : " hours.");
	else
		msg << " until /unpink.";
	if(Player* gm = dynamic_cast<Player*>(c))
		gm->sendTextMessage(MSG_BLUE_TEXT, msg.str().c_str());
	target->sendTextMessage(MSG_RED_INFO, "You have been marked with a pink skull: if you die, you lose all your equipment.");
	return true;
}

bool Commands::unpinkSkull(Creature* c, const std::string &cmd, const std::string &param)
{
	std::string name = pinkTrim(param);
	Player* target = pinkTarget(game, c, name, "unmark");
	if(!target)
		return true;
	if(target->skullType != SKULL_PINK) {
		c->sendCancel("That player has no pink skull.");
		return true;
	}
	target->skullType = SKULL_NONE;
	target->skullTicks = 0;
	game->Skull(target);
	IOPlayer::instance()->savePlayer(target);
	if(Player* gm = dynamic_cast<Player*>(c))
		gm->sendTextMessage(MSG_BLUE_TEXT, (target->getName() + " no longer has a pink skull.").c_str());
	target->sendTextMessage(MSG_INFO, "Your pink skull has been removed.");
	return true;
}

bool Commands::goUp(Creature* c, const std::string &cmd, const std::string &param)
{
	Position pos = c->pos;
	pos.z--;
	game->teleport(c, pos);
	return true;
}

bool Commands::goDown(Creature* c, const std::string &cmd, const std::string &param)
{
	Position pos = c->pos;
	pos.z++;
	game->teleport(c, pos);
	return true;
}

bool Commands::showExpForLvl(Creature* c, const std::string &cmd, const std::string &param)
{
	Player *player = dynamic_cast<Player*>(c);

	if (player)
	{
		std::string msg = std::string("You need ") + str(player->getExpForNextLevel()) +
			std::string(" experience points to gain level.");
		player->sendTextMessage(MSG_BLUE_TEXT, msg.c_str());
	}
	return true;
}

bool Commands::showManaForLvl(Creature* c, const std::string &cmd, const std::string &param)
{
	Player *player = dynamic_cast<Player*>(c);

	if (player)
	{
		std::string msg = std::string("You need to spent ") + str(player->getManaForNextMLevel()) +
			std::string(" mana to gain magic level.");
		player->sendTextMessage(MSG_BLUE_TEXT, msg.c_str());
	}

	return true;
}

bool Commands::report(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);

	if (player)
	{
		char buf[64];
		time_t ticks = time(0);

		strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M", localtime(&ticks));

		std::ofstream out("report.log", std::ios::app);
		out << '[' << buf << "] " << player->getName() << ": " << param << std::endl;
		out.close();

		player->sendTextMessage(MSG_BLUE_TEXT, "Your report has been sent.");
	}

	return true;
}

bool Commands::whoIsOnline(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);

	if (player)
	{
		player->sendTextMessage(MSG_BLUE_TEXT, "Players online: ");
		AutoList<Player>::listiterator iter = Player::listPlayer.list.begin();
		std::string info;
		int count = 0;

		while (iter != Player::listPlayer.list.end())
		{
			Player* onlinePlayer = (*iter).second;
			std::stringstream line;
			line << onlinePlayer->getName() << " [" << onlinePlayer->getLevel() << "], ";
			info += line.str();
			++iter;
			++count;

			if (count % 10 == 0)
			{
				player->sendTextMessage(MSG_BLUE_TEXT, info.c_str());
				info.clear();
			}
		}

		if (!info.empty())
			player->sendTextMessage(MSG_BLUE_TEXT, info.c_str());
	}

	return true;
}

bool Commands::setWorldType(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);

	if (player && !param.empty())
	{
		int type = atoi(param.c_str());

		if (type == 0)
		{
			game->setWorldType(WORLD_TYPE_NO_PVP);
			player->sendTextMessage(MSG_BLUE_TEXT, "World type set to no-pvp.");
		}
		else if (type == 1)
		{
			game->setWorldType(WORLD_TYPE_PVP);
			player->sendTextMessage(MSG_BLUE_TEXT, "World type set to pvp.");
		}
		else if (type == 2)
		{
			game->setWorldType(WORLD_TYPE_PVP_ENFORCED);
			player->sendTextMessage(MSG_BLUE_TEXT, "World type set to pvp-enforced.");
		}
	}

	return true;
}

bool Commands::teleportPlayerTo(Creature* c, const std::string &cmd, const std::string &param)
{
	Position pos;
	std::string name;
	std::istringstream in(param.c_str());

	std::getline(in, name, ',');
	in >> pos.x >> pos.y >> pos.z;

	Creature* creature = game->getCreatureByName(name);
	Player* player = dynamic_cast<Player*>(creature);

	if (player)
		game->teleport(player, pos);

	return true;
}

bool Commands::banCharacter(Creature* c, const std::string &cmd, const std::string &param)
{
	Creature* creature = game->getCreatureByName(param);
	Player* player = dynamic_cast<Player*>(creature);

	if (player)
		player->banned = true;

	return true;
}

bool Commands::showPos(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);
	if (player)
	{
		std::stringstream msg;
		msg << "Your position is: " << player->pos.x << ' ' << player->pos.y << ' ' << player->pos.z << std::ends;
		player->sendTextMessage(MSG_BLUE_TEXT, msg.str().c_str());
	}
	return true;
}

bool Commands::showUptime(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);
	if (player)
	{
		uint64_t uptime = (OTSYS_TIME() - Status::instance()->start)/1000;
		int h = (int)floor(uptime / 3600.0);
		int m = (int)floor((uptime - h*3600) / 60.0);
		int s = (int)(uptime - h*3600 - m*60);

		std::stringstream msg;
		msg << "Server has been running for " << h << (h != 1? " hours " : " hour ") <<
			m << (m != 1? " minutes " : " minute ") << s << (s != 1? " seconds. " : " second.") << std::ends;

		player->sendTextMessage(MSG_BLUE_TEXT, msg.str().c_str());
	}
	return true;
}

bool Commands::showPz(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);

	if (player)
	{
		std::ostringstream info;
		if (player->inFightTicks < 1000 && !player->pzLocked)
			info << "No tienes PZ lock." << std::ends;
		else
		{
			long ms = player->inFightTicks >= 1000 ? player->inFightTicks : 0;
			if (ms >= 60000)
				info << "La PZ se quita en " << tickstr(ms) << "." << std::ends;
			else
			{
				int sec = (int)((ms + 999) / 1000);
				info << "La PZ se quita en " << sec << (sec == 1 ? " segundo." : " segundos.") << std::ends;
			}
		}
		player->sendTextMessage(MSG_BLUE_TEXT, info.str().c_str());
	}

	return true;
}

bool Commands::setMaxPlayers(Creature* c, const std::string &cmd, const std::string &param)
{
	if (!param.empty())
	{
		int newmax = atoi(param.c_str());
		if (newmax > 0)
		{
			game->setMaxPlayers(newmax);

			Player* player = dynamic_cast<Player*>(c);
			if (player)
				player->sendTextMessage(MSG_BLUE_TEXT, (std::string("Max number of players is now ")+param).c_str());
		}
	}
	return true;
}

bool Commands::reloadRights(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);

	if (player)
	{
		player->houseRightsChanged = true;
		player->sendTextMessage(MSG_BLUE_TEXT, "House rights reloaded.");
	}

	return true;
}

bool Commands::setHouseOwner(Creature* c, const std::string &cmd, const std::string &param)
{
	Tile* tile = game->getTile(c->pos);
	House* house = tile? tile->getHouse() : NULL;

	if (house)
	{
		Creature* creature = game->getCreatureByName(house->getOwner());
		Player* prevOwner = creature? dynamic_cast<Player*>(creature) : NULL;

		house->setOwner(param);

		creature = game->getCreatureByName(param);
		Player* newOwner = creature? dynamic_cast<Player*>(creature) : NULL;

		if (prevOwner)
			prevOwner->houseRightsChanged = true;
		if (newOwner)
			newOwner->houseRightsChanged = true;
	}
	return true;
}

// Casa a la que apunta el jugador: la casilla que mira (la puerta, desde afuera) o la que pisa.
static House* houseInFrontOf(Game* game, Player* player)
{
	Position front = player->pos;
	switch (player->getDirection())
	{
		case NORTH: front.y--; break;
		case SOUTH: front.y++; break;
		case EAST:  front.x++; break;
		case WEST:  front.x--; break;
		default: break;
	}
	Tile* tile = game->getTile(front);
	if (tile && tile->getHouse())
		return tile->getHouse();
	tile = game->getTile(player->pos);
	return tile ? tile->getHouse() : NULL;
}

static unsigned long housePrice(const House* house)
{
	return (unsigned long)house->getTileCount() * (unsigned long)g_config.HOUSE_PRICE_PER_TILE;
}

// Movibles que quedan en la casa (en el suelo o colgados). Cuentan para !leavehouse.
static int movableItemsInHouse(Game* game, const House* house)
{
	int count = 0;
	std::vector<Position> all = house->tiles;
	all.insert(all.end(), house->wallTiles.begin(), house->wallTiles.end());   // lo colgado en las paredes
	for (size_t i = 0; i < all.size(); i++)
	{
		Tile* tile = game->getTile(all[i]);
		if (!tile)
			continue;
		for (ItemVector::const_iterator it = tile->downItems.begin(); it != tile->downItems.end(); ++it)
			if (!(*it)->isNotMoveable())
				count++;
		for (ItemVector::const_iterator it = tile->topItems.begin(); it != tile->topItems.end(); ++it)
			if (!(*it)->isNotMoveable())
				count++;
	}
	return count;
}

bool Commands::buyHouse(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);
	if (!player)
		return true;

	House* house = houseInFrontOf(game, player);
	if (!house)
	{
		player->sendCancel("Mira la puerta de la casa que quieres comprar y escribe !buyhouse.");
		return true;
	}

	unsigned long price = housePrice(house);
	std::ostringstream info;

	if (!house->getOwner().empty())
	{
		info << "La casa '" << house->getName() << "' ya tiene dueÒo: " << house->getOwner() << ".";
		player->sendCancel(info.str().c_str());
		return true;
	}

	House* owned = Houses::GetHouseByOwner(player->getName());
	if (owned)
	{
		info << "Ya tienes la casa '" << owned->getName() << "'. Escribe !leavehouse para dejarla antes de comprar otra.";
		player->sendCancel(info.str().c_str());
		return true;
	}

	if (player->getLevel() < g_config.HOUSE_MIN_LEVEL)
	{
		info << "Necesitas nivel " << g_config.HOUSE_MIN_LEVEL << " para comprar una casa.";
		player->sendCancel(info.str().c_str());
		return true;
	}

	if (!player->canPayWithBank(price) || !player->removeCoinsWithBank(price))
	{
		info << "La casa '" << house->getName() << "' cuesta " << price << " gp (" << house->getTileCount()
		     << " casillas x " << g_config.HOUSE_PRICE_PER_TILE << "). No te alcanza entre lo que llevas y el banco.";
		player->sendCancel(info.str().c_str());
		return true;
	}

	house->clearRights();
	house->setOwner(player->getName());
	house->save();
	player->houseRightsChanged = true;

	info << "Compraste la casa '" << house->getName() << "' por " << price << " gp. Ya es tuya.";
	player->sendTextMessage(MSG_ADVANCE, info.str().c_str());
	std::cout << ":: house bought: " << house->getName() << " by " << player->getName()
	          << " for " << price << " gp" << std::endl;
	return true;
}

bool Commands::leaveHouse(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);
	if (!player)
		return true;

	House* house = Houses::GetHouseByOwner(player->getName());
	if (!house)
	{
		player->sendCancel("No tienes ninguna casa.");
		return true;
	}

	std::ostringstream info;
	int left = movableItemsInHouse(game, house);
	if (left > 0)
	{
		info << "TodavÌa hay " << left << (left == 1 ? " objeto" : " objetos")
		     << " en la casa '" << house->getName() << "'. " << (left == 1 ? "S·calo" : "S·calos")
		     << " antes de dejarla.";
		player->sendCancel(info.str().c_str());
		return true;
	}

	house->clearRights();
	house->save();
	player->houseRightsChanged = true;

	info << "Dejaste la casa '" << house->getName() << "'. Ya no es tuya (no se devuelve el dinero).";
	player->sendTextMessage(MSG_BLUE_TEXT, info.str().c_str());
	std::cout << ":: house left: " << house->getName() << " by " << player->getName() << std::endl;
	return true;
}

bool Commands::gmInvisible(Creature* c, const std::string &cmd, const std::string &param)
{
	Player *player = dynamic_cast<Player*>(c);

	if (!player->gmInvisible)
	{
		player->oldlookhead = player->lookhead;
		player->oldlookbody = player->lookbody;
		player->oldlooklegs = player->looklegs;
		player->oldlookfeet = player->lookfeet;
		player->oldlooktype = player->looktype;
		player->oldlookcorpse = player->lookcorpse;
		player->oldlookmaster = player->lookmaster;
		player->gmInvisible = true;
		player->looktype = GM_GHOST_LOOKTYPE;   // se ve como un Ghost; los demas no lo ven

		Tile* tile = game->getTile(player->pos.x,player->pos.y,player->pos.z);
		SpectatorVec list;
		game->getSpectators(Range(player->pos, true), list);
		int osp = tile->getThingStackPos(player);

		for(SpectatorVec::iterator it = list.begin(); it != list.end(); ++it)
			if((*it) != player && (*it)->access == 0)
				(*it)->onCreatureDisappear(player, osp, true);

		// Ya invisible: pasa abajo de las demas criaturas de la casilla (ver Tile::addThing).
		if(tile->removeThing(player))
			tile->addThing(player);

		player->sendTextMessage(MSG_INFO, "You are invisible.");
		game->creatureBroadcastTileUpdated(player->pos);   // le llega el Ghost al GM (y a los de igual o mas access)
	}
	else
	{
		player->gmInvisible = false;
		player->looktype = player->oldlooktype;   // vuelve su outfit (lo guardado en disco es lookmaster: nunca el Ghost)
		Tile* tilee = game->getTile(player->pos.x,player->pos.y,player->pos.z);

		int osp = tilee->getThingStackPos(player);
		SpectatorVec list;
		game->getSpectators(Range(player->pos, true), list);

		for(SpectatorVec::iterator it = list.begin(); it != list.end(); ++it)
			game->creatureBroadcastTileUpdated(player->pos);

		game->creatureChangeOutfit(player);
		player->sendTextMessage(MSG_INFO, "You are visible again.");
	}

	return true;
}

bool Commands::showFrags(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);

	if (player)
	{
		std::ostringstream info;
		info << "You have " << player->skullKills
			<< " unjustified kills. You will lose a frag in " << tickstr(player->absolveTicks) << '.' << std::ends;
		player->sendTextMessage(MSG_BLUE_TEXT, info.str().c_str());
	}

	return true;
}

bool Commands::forceServerSave(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);
	if (player)
	{
		game->serverSave();
		player->sendTextMessage(MSG_BLUE_TEXT, "Server save completed.");
	}
	return true;
}

bool Commands::shutdown(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);
	if (player && !param.empty())
		game->sheduleShutdown(atoi(param.c_str()));
	return true;
}

bool Commands::cleanMap(Creature* c, const std::string &cmd, const std::string &param)
{
	std::ostringstream info;
	Player* player = dynamic_cast<Player*>(c);

	if (player)
	{
		std::cout << ":: cleanup... ";

		timer();
		long count = game->cleanMap();
		double sec = timer();

		info << "Clean completed. Collected " << count << (count==1? " item." : " items.") << std::ends;
		player->sendTextMessage(MSG_BLUE_TEXT, info.str().c_str());

		std::cout << "ok (" << sec << " s)\n";
	}
	return true;
}

bool Commands::premmy(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);
	int hours;
	std::string name;
	std::istringstream in(param.c_str());

	in >> hours;
	std::getline(in, name);
	name = name.substr(1);

	if (in)
	{
		Creature* creature = game->getCreatureByName(name);
		Player* target = creature? dynamic_cast<Player*>(creature) : NULL;

		if (target)
			target->premiumTicks += 1000*60*60*hours;
	}

	return true;
}

bool Commands::showPremmy(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);

	if (player)
	{
		std::ostringstream info;
		if (g_config.FREE_PREMMY)
			info << "You have unlimited premium account." << std::ends;
		else
			info << "You have " << tickstr(player->premiumTicks) << " of premium time left." << std::ends;
		player->sendTextMessage(MSG_BLUE_TEXT, info.str().c_str());
	}

	return true;
}

bool Commands::promote(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);
	Creature* creature = game->getCreatureByName(param);
	Player* target = dynamic_cast<Player*>(creature);

	if (target) {
		target->promote();
	}

	return true;
}

//////////////////////////////////////////////////////////////////////
// Comandos de GM para probar contenido (nov 2026). Doc: docs/gameplay/GM_COMANDOS.md
//////////////////////////////////////////////////////////////////////


// Resuelve el jugador objetivo: el nombre dado (online) o el mismo GM.
static Player* gmTarget(Game* game, Creature* c, const std::string& name)
{
	if(name.empty())
		return dynamic_cast<Player*>(c);
	return game->getPlayerByName(name);
}

bool Commands::gmGod(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);
	if(!player)
		return true;

	player->gmMortal = !player->gmMortal;
	if(player->gmMortal) {
		gmInfo(player, "God OFF: los monstruos te atacan, recibes danio real (no bajas de 1 de vida) y sin el +1337.");
	}
	else {
		player->health = player->healthmax;
		player->mana = player->manamax;
		gmInfo(player, "God ON: protegido otra vez (vida y mana llenos).");
	}
	player->hasteTicks = 0;
	game->changeSpeed(player->getID(), player->getNormalSpeed());
	player->sendStats();
	return true;
}

bool Commands::gmGoPlace(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* player = dynamic_cast<Player*>(c);
	if(!player)
		return true;

	std::string filename = datadir + "gmplaces.xml";
	xmlDocPtr doc = xmlParseFile(filename.c_str());
	if(!doc) {
		gmInfo(player, "No se pudo leer " + filename + ".");
		return true;
	}

	const std::string wanted = gmLower(gmTrim(param));
	std::string names, foundName;
	Position found;
	bool exact = false, haveMatch = false;

	xmlNodePtr root = xmlDocGetRootElement(doc);
	for(xmlNodePtr p = root ? root->children : NULL; p; p = p->next) {
		if(xmlStrcmp(p->name, (const xmlChar*)"place") != 0)
			continue;
		char* nameAttr = (char*)xmlGetProp(p, (const xmlChar*)"name");
		if(!nameAttr)
			continue;
		std::string name = nameAttr;
		xmlFreeOTSERV(nameAttr);

		int x = 0, y = 0, z = 0;
		readXMLInteger(p, "x", x);
		readXMLInteger(p, "y", y);
		readXMLInteger(p, "z", z);

		names += (names.empty() ? "" : ", ") + name;
		const std::string lname = gmLower(name);
		if(wanted.empty() || exact)
			continue;
		if(lname == wanted || (!haveMatch && lname.compare(0, wanted.size(), wanted) == 0)) {
			exact = (lname == wanted);
			haveMatch = true;
			foundName = name;
			found = Position(x, y, z);
		}
	}
	xmlFreeDoc(doc);

	if(wanted.empty() || !haveMatch) {
		if(!wanted.empty())
			gmInfo(player, "No conozco el lugar \"" + param + "\".");
		gmInfo(player, "Lugares: " + names + ".");
		return true;
	}

	// Si la casilla esta ocupada, la libre mas cercana (hasta 3 de distancia).
	Position dest = found;
	if(!gmFreeTile(game->getTile(dest.x, dest.y, dest.z))) {
		bool ok = false;
		for(int d = 1; d <= 3 && !ok; ++d)
			for(int dx = -d; dx <= d && !ok; ++dx)
				for(int dy = -d; dy <= d && !ok; ++dy)
					if(gmFreeTile(game->getTile(found.x + dx, found.y + dy, found.z))) {
						dest = Position(found.x + dx, found.y + dy, found.z);
						ok = true;
					}
		if(!ok) {
			gmInfo(player, "El lugar " + foundName + " no tiene casilla libre.");
			return true;
		}
	}

	game->teleport(player, dest);
	game->sendMagicEffect(dest, NM_ME_ENERGY_AREA);
	return true;
}

bool Commands::gmSetLevel(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* self = dynamic_cast<Player*>(c);
	long newLevel;
	std::string name;
	if(!gmSplitLeadingNumber(param, newLevel, name)) {
		gmInfo(self, "Uso: /nivel 100  o  /nivel 100 Nombre");
		return true;
	}
	Player* target = gmTarget(game, c, name);
	if(!target) {
		gmInfo(self, "No esta online: " + name + ".");
		return true;
	}
	newLevel = gmClamp(newLevel, 1, 1000);

	const int oldLevel = target->level;
	const int voc = (int)target->vocation;
	if(newLevel > oldLevel) {
		target->addExp(target->getExpForLv(newLevel) - target->experience);
	}
	else if(newLevel < oldLevel) {
		while(target->level > newLevel) {
			target->level--;
			target->healthmax = std::max<int64_t>(1, target->healthmax - g_config.HP_GAIN[voc]);
			target->manamax = std::max<int64_t>(0, target->manamax - g_config.MANA_GAIN[voc]);
			target->capacity = std::max(0.0, target->capacity - g_config.CAP_GAIN[voc]);
		}
		target->experience = target->getExpForLv(newLevel);
		target->health = std::min(target->health, target->healthmax);
		target->mana = std::min(target->mana, target->manamax);
		target->setNormalSpeed();
		game->changeSpeed(target->getID(), target->getSpeed());
		std::stringstream msg;
		msg << "You were downgraded from level " << oldLevel << " to level " << newLevel << ".";
		target->sendTextMessage(MSG_ADVANCE, msg.str().c_str());
	}
	else {
		// mismo nivel: deja la experiencia justo al inicio del nivel
		target->experience = target->getExpForLv(newLevel);
	}
	target->reconcileCapacity();
	target->sendStats();

	std::stringstream info;
	info << target->getName() << ": nivel " << oldLevel << " -> " << newLevel << ".";
	gmInfo(self, info.str());
	return true;
}

bool Commands::gmSetSkill(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* self = dynamic_cast<Player*>(c);
	std::string p = gmTrim(param);
	std::string::size_type sp = p.find(' ');
	const std::string skillName = gmLower(sp == std::string::npos ? p : p.substr(0, sp));
	long value;
	std::string name;
	if(sp == std::string::npos || !gmSplitLeadingNumber(p.substr(sp + 1), value, name)) {
		gmInfo(self, "Uso: /skill sword 90 [Nombre]. Skills: fist, club, sword, axe, distance, shielding, fishing.");
		return true;
	}

	int skill = -1;
	if(skillName == "fist" || skillName == "puno") skill = SKILL_FIST;
	else if(skillName == "club" || skillName == "maza") skill = SKILL_CLUB;
	else if(skillName == "sword" || skillName == "espada") skill = SKILL_SWORD;
	else if(skillName == "axe" || skillName == "hacha") skill = SKILL_AXE;
	else if(skillName == "distance" || skillName == "dist" || skillName == "distancia") skill = SKILL_DIST;
	else if(skillName == "shielding" || skillName == "shield" || skillName == "escudo") skill = SKILL_SHIELD;
	else if(skillName == "fishing" || skillName == "fish" || skillName == "pesca") skill = SKILL_FISH;
	if(skill < 0) {
		gmInfo(self, "Skill desconocido: " + skillName + ". Skills: fist, club, sword, axe, distance, shielding, fishing.");
		return true;
	}

	Player* target = gmTarget(game, c, name);
	if(!target) {
		gmInfo(self, "No esta online: " + name + ".");
		return true;
	}
	value = gmClamp(value, 10, 300);
	target->skills[skill][SKILL_LEVEL] = value;
	target->skills[skill][SKILL_TRIES] = 0;
	target->skills[skill][SKILL_PERCENT] = 0;
	target->sendSkills();

	std::stringstream info;
	info << target->getName() << ": " << skillName << " " << value << ".";
	gmInfo(self, info.str());
	return true;
}

bool Commands::gmSetMagicLevel(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* self = dynamic_cast<Player*>(c);
	long value;
	std::string name;
	if(!gmSplitLeadingNumber(param, value, name)) {
		gmInfo(self, "Uso: /ml 60  o  /ml 60 Nombre");
		return true;
	}
	Player* target = gmTarget(game, c, name);
	if(!target) {
		gmInfo(self, "No esta online: " + name + ".");
		return true;
	}
	value = gmClamp(value, 0, 200);
	target->maglevel = value;
	target->manaspent = 0;
	target->sendStats();

	std::stringstream info;
	info << target->getName() << ": magic level " << value << ".";
	gmInfo(self, info.str());
	return true;
}

bool Commands::gmLootTest(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* self = dynamic_cast<Player*>(c);
	std::string monsterName;
	long kills;
	gmSplitTrailingNumber(param, monsterName, kills, 100);
	kills = gmClamp(kills, 1, 10000);

	MonsterType* mType = g_monsters.getMonsterType(g_monsters.getIdByName(monsterName));
	if(!mType) {
		gmInfo(self, "Uso: /loot frost dragon 500. Monstruo desconocido: " + monsterName + ".");
		return true;
	}

	std::map<unsigned short, GmLootCount> counts;
	for(long i = 0; i < kills; ++i) {
		Item* corpseItem = Item::CreateItem(mType->lookcorpse);
		Container* corpse = dynamic_cast<Container*>(corpseItem);
		if(!corpse) {
			if(corpseItem)
				corpseItem->releaseThing();
			corpseItem = Item::CreateItem(1988);   // backpack
			corpse = dynamic_cast<Container*>(corpseItem);
			if(!corpse) {
				if(corpseItem)
					corpseItem->releaseThing();
				gmInfo(self, "No se pudo crear el cadaver para simular.");
				return true;
			}
		}
		mType->createLoot(corpse, NULL);
		gmCountLoot(corpse, counts);
		corpse->releaseThing();
	}

	std::vector< std::pair<unsigned short, GmLootCount> > rows(counts.begin(), counts.end());
	std::sort(rows.begin(), rows.end(), gmLootSort);

	unsigned long gold = 0;
	for(size_t i = 0; i < rows.size(); ++i) {
		if(rows[i].first == ITEM_COINS_GOLD) gold += rows[i].second.total;
		else if(rows[i].first == ITEM_COINS_PLATINUM) gold += rows[i].second.total * 100;
		else if(rows[i].first == ITEM_COINS_CRYSTAL) gold += rows[i].second.total * 10000;
	}

	std::stringstream head;
	head << "Loot de " << mType->name << " en " << kills << " muertes (sin bonus premium): "
		<< rows.size() << " items distintos, " << gold << " gp en monedas (" << (gold / kills) << " por muerte).";
	gmInfo(self, head.str());

	const size_t maxRows = 40;
	for(size_t i = 0; i < rows.size() && i < maxRows; ++i) {
		const GmLootCount& lc = rows[i].second;
		std::stringstream line;
		line << "  " << Item::items[rows[i].first].name << " (" << rows[i].first << "): "
			<< lc.drops << " veces (" << (lc.drops * 1000 / kills) / 10.0 << "%)";
		if(lc.total != lc.drops)
			line << ", " << lc.total << " en total";
		gmInfo(self, line.str());
	}
	if(rows.size() > maxRows) {
		std::stringstream more;
		more << "  ... y " << (rows.size() - maxRows) << " items mas.";
		gmInfo(self, more.str());
	}
	return true;
}

bool Commands::gmKillMonsters(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* self = dynamic_cast<Player*>(c);
	SpectatorVec list;
	game->getSpectators(Range(c->pos, false), list);

	std::vector<Monster*> victims;
	for(SpectatorVec::iterator it = list.begin(); it != list.end(); ++it) {
		Monster* monster = dynamic_cast<Monster*>(*it);
		// los invocados se van con su duenio (removeCreature saca los summons)
		if(monster && !monster->isRemoved && !monster->getMaster())
			victims.push_back(monster);
	}

	long removed = 0;
	for(size_t i = 0; i < victims.size(); ++i) {
		const Position pos = victims[i]->pos;
		if(game->removeCreature(victims[i])) {
			game->sendMagicEffect(pos, NM_ME_PUFF);
			removed++;
		}
	}

	std::stringstream info;
	info << "Monstruos eliminados: " << removed << " (los spawns los vuelven a poner).";
	gmInfo(self, info.str());
	return true;
}

bool Commands::gmSpeed(Creature* c, const std::string &cmd, const std::string &param)
{
	Player* self = dynamic_cast<Player*>(c);
	std::string p = gmTrim(param);
	if(p.empty() || !gmIsNumber(p))
		c->gmSpeed = 0;
	else
		c->gmSpeed = gmClamp(atol(p.c_str()), 50, 1500);

	c->hasteTicks = 0;
	game->changeSpeed(c->getID(), c->getNormalSpeed());

	std::stringstream info;
	if(c->gmSpeed > 0)
		info << "Velocidad fija: " << c->gmSpeed << ". /speed sin numero la vuelve a la normal.";
	else
		info << "Velocidad normal: " << c->getNormalSpeed() << ".";
	gmInfo(self, info.str());
	return true;
}

// Resumen de comandos que ve el GM al entrar y con /comandos (docs/gameplay/GM_COMANDOS.md).
// Si se agrega un comando de GM, sumarlo aca.
static const char* GM_HELP_SECTIONS[] = {
	"Comandos de GM (/comandos los muestra de nuevo)",

	"MOVERSE\n"
	"/ir [lugar] - viajar a un lugar (sin nombre: lista)\n"
	"/goto Nombre  o  /goto x y z - ir a un jugador o a coordenadas\n"
	"/a N - avanzar N casillas hacia donde miras\n"
	"/up, /down - subir o bajar un piso\n"
	"/t - ir a tu templo\n"
	"/c Nombre - traer a un jugador o criatura\n"
	"/send Nombre, x y z - mandar a un jugador a coordenadas\n"
	"/pos - tu posicion\n"
	"/invisible - nadie te ve, te ves como Ghost y pasas por encima de todos\n"
	"/speed [N] - velocidad fija (sin numero: la normal)",

	"PROBAR CONTENIDO\n"
	"/god - apaga/prende la proteccion (apagada: te atacan, no bajas de 1 de vida)\n"
	"/i nombre o id [cantidad] - crear item (ej: /i black fire sword)\n"
	"/m monstruo - poner un monstruo adelante\n"
	"/summon monstruo - invocar un monstruo tuyo\n"
	"/s npc - poner un NPC adelante\n"
	"/matar - sacar los monstruos a la vista\n"
	"/loot monstruo [N] - simular el loot de N muertes (ej: /loot frost dragon 500)\n"
	"/nivel N [Nombre] - cambiar nivel\n"
	"/skill sword 90 [Nombre] - fist club sword axe distance shielding fishing\n"
	"/ml N [Nombre] - cambiar magic level\n"
	"/promote Nombre - promocionar\n"
	"/z N - ver el efecto magico N\n"
	"/q [N] - ver tu dinero o descontar N\n"
	"Look: ids, action/unique id, items de la casilla; criaturas con vida y pos",

	"JUGADORES\n"
	"/info Nombre - datos del jugador\n"
	"/getonline, /ips - quien esta online y sus IP\n"
	"/kick Nombre - sacarlo del juego\n"
	"/b Nombre - ban de IP  |  /ban Nombre - ban del personaje\n"
	"/pink Nombre[, horas]  |  /unpink Nombre - calavera rosa\n"
	"/owner Nombre - duenio de la casa donde estas parado\n"
	"/B texto - mensaje a todo el servidor",

	"SERVIDOR\n"
	"/save - guardar ahora\n"
	"/clean - limpiar los items del piso\n"
	"/reload actions|commands|monsters|spells|config\n"
	"/closeserver, /openserver - cerrar o abrir a los jugadores\n"
	"/max N - maximo de jugadores\n"
	"/pvp 0|1|2 - no-pvp, pvp, pvp-enforced\n"
	"/shutdown N - apagar en N minutos",
};

void sendGmCommandsHelp(Player* player)
{
	if(!player)
		return;
	for(size_t i = 0; i < sizeof(GM_HELP_SECTIONS) / sizeof(GM_HELP_SECTIONS[0]); ++i)
		player->sendTextMessage(MSG_BLUE_TEXT, GM_HELP_SECTIONS[i]);
}

bool Commands::gmHelp(Creature* c, const std::string &cmd, const std::string &param)
{
	sendGmCommandsHelp(dynamic_cast<Player*>(c));
	return true;
}
