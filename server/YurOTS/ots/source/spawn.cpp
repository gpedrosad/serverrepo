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

#include "spawn.h"
#include "game.h"
#include "player.h"
#include "npc.h"
#include "monster.h"

#include <libxml/xmlmemory.h>
#include <libxml/parser.h> 

extern LuaScript g_config;

namespace {
static bool isRageVariantSpawnName(const std::string& name)
{
	return (name.size() >= 6 && name.compare(0, 6, "Angry ") == 0) ||
		(name.size() >= 8 && name.compare(0, 8, "Furious ") == 0) ||
		(name.size() >= 9 && name.compare(0, 9, "Enraged ") == 0);
}
}

SpawnManager* SpawnManager::_instance = NULL;
Game* SpawnManager::game = NULL;
spawnsList SpawnManager::spawns;

SpawnManager::SpawnManager()
{
	//
}

SpawnManager::~SpawnManager()
{
	for(spawnsList::iterator it = spawns.begin(); it != spawns.end(); ++it)
		delete *it;

	spawns.clear();
}

bool SpawnManager::initialize(Game *igame)
{
	game = igame;
	_instance = new SpawnManager();
	return (_instance != NULL);
}

SpawnManager* SpawnManager::instance() {
	return _instance;
}

bool SpawnManager::addSpawn(Spawn* spawn)
{
	spawns.push_back(spawn);
	return true;
}

bool SpawnManager::loadSpawnsXML(std::string filename)
{
	std::transform(filename.begin(), filename.end(), filename.begin(), tolower);
	xmlDocPtr doc = xmlParseFile(filename.c_str());

	if (doc){
		xmlNodePtr root, p;
		char* nodeValue = NULL;
		root = xmlDocGetRootElement(doc);

		root = xmlDocGetRootElement(doc);

		if (xmlStrcmp(root->name,(const xmlChar*) "spawns")){			
			xmlFreeDoc(doc);
			return false;
		}

		p = root->children;

		while (p) {
			const char* str = (char*)p->name;

			if (strcmp(str, "spawn") == 0) {
				Position centerpos;
				int radius;

				nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"centerx");
				if(nodeValue) {
					centerpos.x = atoi(nodeValue);
					xmlFreeOTSERV(nodeValue);
				}
				else {
					xmlFreeOTSERV(nodeValue);
					return false;
				}

				nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"centery");
				if(nodeValue) {
					centerpos.y = atoi(nodeValue);
					xmlFreeOTSERV(nodeValue);
				}
				else {
					xmlFreeOTSERV(nodeValue);
					xmlFreeDoc(doc);
					return false;
				}

				nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"centerz");
				if(nodeValue) {
					centerpos.z = atoi(nodeValue);
					xmlFreeOTSERV(nodeValue);
				}
				else {
					xmlFreeOTSERV(nodeValue);
					xmlFreeDoc(doc);
					return false;
				}

				nodeValue = (char*)xmlGetProp(p, (const xmlChar *)"radius");
				if(nodeValue) {
					radius = atoi(nodeValue);
					xmlFreeOTSERV(nodeValue);
				}
				else {
					xmlFreeOTSERV(nodeValue);
					xmlFreeDoc(doc);
					return false;
				}

				Spawn *spawn = new Spawn(game, centerpos, radius);
				spawns.push_back(spawn);

				std::string name;
				int x, y, spawntime;
				Direction direction = NORTH;
				int rawdir = 0; //NORTH

				xmlNodePtr tmp = p->children;
				while (tmp) {
					str = (char*)tmp->name;
					if (strcmp(str, "monster") == 0) {
						nodeValue = (char*)xmlGetProp(tmp, (const xmlChar *)"name");
						if(nodeValue) {
							name = nodeValue;
							xmlFreeOTSERV(nodeValue);
						}
						else {
							tmp = tmp->next;
							break;
						}

						nodeValue = (char*)xmlGetProp(tmp, (const xmlChar *)"direction");
						if(nodeValue) {
							rawdir = atoi(nodeValue);
							xmlFreeOTSERV(nodeValue);
						}

						nodeValue = (char*)xmlGetProp(tmp, (const xmlChar *)"x");
						if(nodeValue) {
							x = atoi(nodeValue);
							xmlFreeOTSERV(nodeValue);
						}
						else {
							tmp = tmp->next;
							break;
						}

						nodeValue = (char*)xmlGetProp(tmp, (const xmlChar *)"y");
						if(nodeValue) {
							y = atoi(nodeValue);
							xmlFreeOTSERV(nodeValue);
						}
						else {
							tmp = tmp->next;
							break;
						}

						nodeValue = (char*)xmlGetProp(tmp, (const xmlChar *)"spawntime");
						if(nodeValue) {
							spawntime = atoi(nodeValue);
							xmlFreeOTSERV(nodeValue);
						}
						else {
							tmp = tmp->next;
							break;
						}

						switch(rawdir) {
							case 0: direction = NORTH; break;
							case 1: direction = EAST; break;
							case 2: direction = SOUTH; break;
							case 3: direction = WEST; break;

							default:
								direction = NORTH;
								break;
						}

						spawn->addMonster(name, direction, x, y, spawntime * 1000);
					}

					tmp = tmp->next;
				}
			}

			p = p->next;
		}

		xmlFreeDoc(doc);
		return true;
	}

	return false;
}

bool SpawnManager::startup()
{
	for(spawnsList::iterator it = spawns.begin(); it != spawns.end(); ++it) {
		(*it)->startup();
	}

	if(!spawns.empty()) {
		game->addEvent(makeTask(20000, std::bind2nd(std::mem_fun(&Game::checkSpawns), 20000)));
	}

	return true;
}

void SpawnManager::checkSpawns(int t)
{
	for(spawnsList::iterator it = spawns.begin(); it != spawns.end(); ++it) {
		(*it)->idle(t);
	}
}

Spawn::Spawn(Game *igame, Position pos, int _radius)
{
	game = igame;
	centerPos = pos;
	radius = _radius;
}

bool Spawn::startup()
{
	for(SpawnMap::iterator sit = spawnmap.begin(); sit != spawnmap.end(); ++sit) {
		respawn(sit->first, sit->second.pos, sit->second.name, sit->second.dir);
	}

	return true;
}

bool Spawn::addMonster(std::string name, Direction dir, int x, int y, int spawntime)
{
	Position tmpPos(centerPos.x + x, centerPos.y, centerPos.z);
	if(!isInSpawnRange(tmpPos)) {
// #ifdef __DEBUG__
		std::cout << "Monster is outside the spawn-area!" << std::endl;
// #endif
		return false;
	}

	struct spawninfo si;
	si.name = name;
	si.dir = dir;
	si.pos.x = centerPos.x + x;
	si.pos.y = centerPos.y + y;
	si.pos.z = centerPos.z;
	si.spawntime = spawntime;
	// Gameplay jul 2026: rage variants placed on the map respawn 4x slower.
	if(isRageVariantSpawnName(name)) {
		si.spawntime *= 4;
	}
	si.lastspawn = 0;

	unsigned long spawnid = (int)spawnmap.size() + 1;
	spawnmap[spawnid] = si;

	return true;
}

Monster* Spawn::respawn(unsigned long spawnid, Position &pos, std::string &name, Direction dir)
{

	Monster* monster = Monster::createMonster(name, game);
	if(monster){

		monster->setDirection(dir);
		monster->masterPos = centerPos;

		if(game->placeCreature(pos, monster)) {
			monster->useThing();
			spawnedmap.insert(spawned_pair(spawnid, monster));
			spawnmap[spawnid].lastspawn = OTSYS_TIME();
			return monster;
		}

		//not loaded, or could not place it on the map
		delete monster;
		monster = NULL;
	}
	return NULL;
}

bool Spawn::isInSpawnRange(const Position &p)
{
	if ((p.x >= centerPos.x - radius) && (p.x <= centerPos.x + radius) &&
      (p.y >= centerPos.y - radius) && (p.y <= centerPos.y + radius))
    return true;

	return false;
}

void Spawn::idle(int t)
{
	SpawnedMap::iterator it;
	for(it = spawnedmap.begin(); it != spawnedmap.end();) {
		if (it->second->isRemoved == true /*it->second->health <= 0*/) {
			if(it->first != 0) {
				spawnmap[it->first].lastspawn = OTSYS_TIME();
			}
			it->second->releaseThing();

			spawnedmap.erase(it++);
		}
		else
			// Keep the original slot occupied even if the monster is lured away.
			// Freeing it here allows the spawn to create duplicates while the
			// original monster is still alive somewhere else in the world.
			++it;
	}

	for(SpawnMap::iterator sit = spawnmap.begin(); sit != spawnmap.end(); ++sit) {

		if(spawnedmap.count(sit->first) == 0) {
			if((OTSYS_TIME() - sit->second.lastspawn) >= sit->second.spawntime) {
				// Gameplay change 2026-07-10: respawn as soon as the slot is free
				// and spawntime elapsed, even if players are watching the tile.
				// Duplicates are prevented by spawnedmap (slot occupied while alive,
				// including monsters lured away from the spawn area).
				respawn(sit->first, sit->second.pos, sit->second.name, sit->second.dir);
			}
		}
	}
}
