//////////////////////////////////////////////////////////////////////
// Private house trainer dummy persistence
//////////////////////////////////////////////////////////////////////

#include "private_trainers.h"

#include "game.h"
#include "houses.h"
#include "luascript.h"
#include "monster.h"
#include "player.h"
#include "tile.h"

#include <libxml/parser.h>
#include <libxml/xmlmemory.h>
#include <libxml/xmlstring.h>

#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <vector>

extern LuaScript g_config;
extern xmlMutexPtr xmlmutex;

const char* PrivateTrainers::MONSTER_NAME = "Private Trainer Dummy";

namespace {
	struct PrivateTrainerEntry {
		Position pos;
	};

	std::vector<PrivateTrainerEntry> privateTrainerEntries;

	std::string getPrivateTrainersFile()
	{
		return g_config.DATA_DIR + "private_trainers.xml";
	}

	bool readIntProp(xmlNodePtr node, const char* key, int& value)
	{
		char* raw = (char*)xmlGetProp(node, (const xmlChar*)key);
		if (!raw)
			return false;

		value = atoi(raw);
		xmlFreeOTSERV(raw);
		return true;
	}

	void setIntProp(xmlNodePtr node, const char* key, int value)
	{
		std::stringstream ss;
		ss << value;
		xmlSetProp(node, (const xmlChar*)key, (const xmlChar*)ss.str().c_str());
	}

	bool isClientTargetPosition(const Position& pos)
	{
		return pos.x > 0 && pos.x != 0xFFFF && pos.y > 0 && pos.z >= 0;
	}

	bool hasTrainerInHouse(Game* game, House* house)
	{
		if (!game || !house)
			return false;

		for (std::vector<PrivateTrainerEntry>::const_iterator it = privateTrainerEntries.begin();
			 it != privateTrainerEntries.end(); ++it) {
			Tile* tile = game->getTile(it->pos);
			if (tile && tile->getHouse() == house)
				return true;
		}

		return false;
	}

	House* getTargetHouse(Game* game, const Position& pos, std::string& message)
	{
		if (!game || !isClientTargetPosition(pos)) {
			message = "Use it on a house tile.";
			return NULL;
		}

		Tile* tile = game->getTile(pos);
		if (!tile || !tile->isHouse() || !tile->getHouse()) {
			message = "You can only place a private trainer inside a house.";
			return NULL;
		}

		return tile->getHouse();
	}

	bool canUseHouse(Player* player, House* house)
	{
		if (!player || !house)
			return false;

		if (player->access >= g_config.ACCESS_HOUSE)
			return true;

		return house->getPlayerRights(player->getName()) == HOUSE_OWNER;
	}

	bool canPlaceOnTile(Game* game, House* house, const Position& pos, std::string& message)
	{
		Tile* tile = game ? game->getTile(pos) : NULL;
		if (!tile || !tile->isHouse() || tile->getHouse() != house) {
			message = "You can only place a private trainer inside a house.";
			return false;
		}

		if (house->getFrontDoor() == pos) {
			message = "You cannot place a private trainer on the house door.";
			return false;
		}

		if (tile->getCreature()) {
			message = "There is already a creature on that tile.";
			return false;
		}

		if (tile->floorChange() || tile->getTeleportItem()) {
			message = "You cannot place a private trainer there.";
			return false;
		}

		return true;
	}

	bool samePosition(const Position& a, const Position& b)
	{
		return a.x == b.x && a.y == b.y && a.z == b.z;
	}

	void rollbackTrainer(Game* game, Monster* monster)
	{
		if (!game || !monster)
			return;

		if (game->removeCreature(monster))
			game->FreeThing(monster);
	}
}

Monster* PrivateTrainers::Spawn(Game* game, const Position& pos, std::string& message)
{
	if (!game) {
		message = "Private trainer is not available right now.";
		return NULL;
	}

	Tile* tile = game->getTile(pos);
	if (!tile) {
		message = "You cannot place a private trainer there.";
		return NULL;
	}

	Monster* monster = Monster::createMonster(MONSTER_NAME, game);
	if (!monster) {
		message = "Private Trainer Dummy monster is not configured.";
		return NULL;
	}

	if (!monster->canMovedTo(tile)) {
		delete monster;
		message = "There is not enough room for a private trainer there.";
		return NULL;
	}

	Position placePos = pos;
	if (!game->placeCreature(placePos, monster)) {
		delete monster;
		message = "There is not enough room for a private trainer there.";
		return NULL;
	}

	if (!samePosition(placePos, pos)) {
		rollbackTrainer(game, monster);
		message = "There is not enough room for a private trainer there.";
		return NULL;
	}

	return monster;
}

bool PrivateTrainers::Load(Game* game)
{
	privateTrainerEntries.clear();

	const std::string filename = getPrivateTrainersFile();
	std::ifstream file(filename.c_str());
	if (!file.good())
		return true;
	file.close();

	xmlMutexLock(xmlmutex);
	xmlDocPtr doc = xmlParseFile(filename.c_str());
	if (!doc) {
		xmlMutexUnlock(xmlmutex);
		std::cout << "Could not load " << filename << "!" << std::endl;
		return false;
	}

	xmlNodePtr root = xmlDocGetRootElement(doc);
	if (!root || xmlStrcmp(root->name, (const xmlChar*)"private_trainers")) {
		xmlFreeDoc(doc);
		xmlMutexUnlock(xmlmutex);
		std::cout << filename << " has an invalid root node." << std::endl;
		return false;
	}

	for (xmlNodePtr node = root->children; node; node = node->next) {
		if (strcmp((const char*)node->name, "trainer") != 0)
			continue;

		Position pos;
		if (!readIntProp(node, "x", pos.x) ||
			!readIntProp(node, "y", pos.y) ||
			!readIntProp(node, "z", pos.z)) {
			std::cout << "Skipping private trainer with invalid coordinates." << std::endl;
			continue;
		}

		std::string message;
		House* house = getTargetHouse(game, pos, message);
		if (!house) {
			std::cout << "Skipping private trainer at " << pos << ": " << message << std::endl;
			continue;
		}

		if (hasTrainerInHouse(game, house)) {
			std::cout << "Skipping duplicate private trainer at " << pos << "." << std::endl;
			continue;
		}

		if (!canPlaceOnTile(game, house, pos, message)) {
			std::cout << "Skipping private trainer at " << pos << ": " << message << std::endl;
			continue;
		}

		Monster* monster = Spawn(game, pos, message);
		if (!monster) {
			std::cout << "Skipping private trainer at " << pos << ": " << message << std::endl;
			continue;
		}

		PrivateTrainerEntry entry;
		entry.pos = pos;
		privateTrainerEntries.push_back(entry);
	}

	xmlFreeDoc(doc);
	xmlMutexUnlock(xmlmutex);
	return true;
}

bool PrivateTrainers::Save()
{
	const std::string filename = getPrivateTrainersFile();
	xmlDocPtr doc;
	xmlNodePtr root, trainerNode;

	xmlMutexLock(xmlmutex);
	doc = xmlNewDoc((const xmlChar*)"1.0");
	doc->children = xmlNewDocNode(doc, NULL, (const xmlChar*)"private_trainers", NULL);
	root = doc->children;

	for (std::vector<PrivateTrainerEntry>::const_iterator it = privateTrainerEntries.begin();
		 it != privateTrainerEntries.end(); ++it) {
		trainerNode = xmlNewNode(NULL, (const xmlChar*)"trainer");
		setIntProp(trainerNode, "x", it->pos.x);
		setIntProp(trainerNode, "y", it->pos.y);
		setIntProp(trainerNode, "z", it->pos.z);
		xmlAddChild(root, trainerNode);
	}

	bool saved = xmlSaveFile(filename.c_str(), doc) != -1;
	if (!saved)
		std::cout << "Could not save " << filename << "!" << std::endl;

	xmlFreeDoc(doc);
	xmlMutexUnlock(xmlmutex);
	return saved;
}

bool PrivateTrainers::Place(Game* game, Player* player, const Position& pos, std::string& message)
{
	House* house = getTargetHouse(game, pos, message);
	if (!house)
		return false;

	if (!canUseHouse(player, house)) {
		message = "Only the house owner can place a private trainer.";
		return false;
	}

	if (hasTrainerInHouse(game, house)) {
		message = "This house already has a private trainer.";
		return false;
	}

	if (!canPlaceOnTile(game, house, pos, message))
		return false;

	Monster* monster = Spawn(game, pos, message);
	if (!monster)
		return false;

	PrivateTrainerEntry entry;
	entry.pos = pos;
	privateTrainerEntries.push_back(entry);

	if (!Save()) {
		privateTrainerEntries.pop_back();
		rollbackTrainer(game, monster);
		message = "Could not save the private trainer. Try again later.";
		return false;
	}

	message = "Your Private Trainer Dummy has been placed.";
	return true;
}
