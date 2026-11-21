//////////////////////////////////////////////////////////////////////
// Padrinazgo (docs/gameplay/PADRINAZGO.md)
//
// Un jugador de nivel 15 o menos le pide a uno de nivel 30 o más que sea su padrino (!padrino Nombre); el
// padrino acepta (!padrino aceptar Nombre) en los 5 minutos siguientes. Cuando el ahijado llega a 20, 35,
// 50, 80 y 100, los dos reciben oro y una caja de regalo de su rango, y se avisa a todo el server. Si el
// padrino no está conectado, su premio queda pendiente y se le da al entrar o al escribir !padrino.
//////////////////////////////////////////////////////////////////////

#include "sponsor.h"
#include "const76.h"
#include "game.h"
#include "item.h"
#include "luascript.h"
#include "player.h"
#include "tools.h"
#include <libxml/parser.h>
#include <libxml/xmlmemory.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fstream>
#include <iostream>
#include <sstream>
#include <vector>

extern LuaScript g_config;
extern Game g_game;
extern xmlMutexPtr xmlmutex;

namespace {
	struct Link {
		std::string child;
		std::string sponsor;
		int childLevel;
		int done;       // bit i: el ahijado llegó al hito i (su premio ya se dio)
		int pending;    // bit i: premio del padrino por el hito i, todavía sin dar
		long since;
	};

	struct Request {
		std::string child;
		std::string sponsor;
		time_t at;
	};

	const int MILESTONES[] = {20, 35, 50, 80, 100};
	const unsigned long CHILD_GOLD[] = {2000, 4000, 8000, 15000, 25000};
	const unsigned long SPONSOR_GOLD[] = {5000, 10000, 20000, 40000, 80000};
	const int MILESTONE_COUNT = 5;
	const int CHILD_MAX_LEVEL = 15;
	const int SPONSOR_MIN_LEVEL = 30;
	const size_t MAX_CHILDREN = 10;
	const time_t REQUEST_SECONDS = 300;
	const unsigned short WELCOME_GIFT = 20354;   // novice gift

	std::vector<Link> links;
	std::vector<Request> requests;

	std::string lower(std::string s)
	{
		std::transform(s.begin(), s.end(), s.begin(), (int(*)(int))tolower);
		return s;
	}

	std::string trim(const std::string& s)
	{
		const std::string::size_type a = s.find_first_not_of(" \t\"");
		if (a == std::string::npos)
			return "";
		const std::string::size_type b = s.find_last_not_of(" \t\"");
		return s.substr(a, b - a + 1);
	}

	bool sameName(const std::string& a, const std::string& b)
	{
		return lower(a) == lower(b);
	}

	std::string fileName()
	{
		return g_config.DATA_DIR + "sponsors.xml";
	}

	Link* findChild(const std::string& name)
	{
		for (size_t i = 0; i < links.size(); ++i)
			if (sameName(links[i].child, name))
				return &links[i];
		return NULL;
	}

	size_t childCount(const std::string& sponsor)
	{
		size_t n = 0;
		for (size_t i = 0; i < links.size(); ++i)
			if (sameName(links[i].sponsor, sponsor))
				++n;
		return n;
	}

	int nextMilestone(int done)
	{
		for (int i = 0; i < MILESTONE_COUNT; ++i)
			if (!(done & (1 << i)))
				return i;
		return -1;
	}

	std::string getProp(xmlNodePtr node, const char* key)
	{
		char* raw = (char*)xmlGetProp(node, (const xmlChar*)key);
		if (!raw)
			return "";
		std::string value(raw);
		xmlFreeOTSERV(raw);
		return value;
	}

	void setProp(xmlNodePtr node, const char* key, const std::string& value)
	{
		xmlSetProp(node, (const xmlChar*)key, (const xmlChar*)value.c_str());
	}

	void setProp(xmlNodePtr node, const char* key, long value)
	{
		std::ostringstream ss;
		ss << value;
		setProp(node, key, ss.str());
	}

	void save()
	{
		const std::string filename = fileName();
		const std::string tmp = filename + ".tmp";
		xmlMutexLock(xmlmutex);
		xmlDocPtr doc = xmlNewDoc((const xmlChar*)"1.0");
		doc->children = xmlNewDocNode(doc, NULL, (const xmlChar*)"sponsors", NULL);
		for (size_t i = 0; i < links.size(); ++i) {
			xmlNodePtr node = xmlNewNode(NULL, (const xmlChar*)"link");
			setProp(node, "child", links[i].child);
			setProp(node, "sponsor", links[i].sponsor);
			setProp(node, "level", (long)links[i].childLevel);
			setProp(node, "done", (long)links[i].done);
			setProp(node, "pending", (long)links[i].pending);
			setProp(node, "since", links[i].since);
			xmlAddChild(doc->children, node);
		}
		// archivo temporal y rename: si se corta a mitad, queda el anterior entero
		const bool saved = xmlSaveFormatFile(tmp.c_str(), doc, 1) != -1 && rename(tmp.c_str(), filename.c_str()) == 0;
		if (!saved)
			std::cout << "Could not save " << filename << "!" << std::endl;
		xmlFreeDoc(doc);
		xmlMutexUnlock(xmlmutex);
	}

	void giveItem(Player* player, unsigned short id, unsigned short count)
	{
		Item* item = Item::CreateItem(id, count);
		if (!item)
			return;
		if (!player->addItem(item))
			g_game.addThing(NULL, player->pos, item);
	}

	void giveGold(Player* player, unsigned long amount)
	{
		const unsigned short coins[] = {ITEM_COINS_CRYSTAL, ITEM_COINS_PLATINUM, ITEM_COINS_GOLD};
		const unsigned long worth[] = {10000, 100, 1};
		for (int c = 0; c < 3; ++c) {
			unsigned long n = amount / worth[c];
			amount -= n * worth[c];
			while (n > 0) {
				const unsigned long stack = std::min<unsigned long>(n, 100);
				giveItem(player, coins[c], (unsigned short)stack);
				n -= stack;
			}
		}
	}

	void broadcast(const std::string& text)
	{
		for (AutoList<Player>::listiterator it = Player::listPlayer.list.begin(); it != Player::listPlayer.list.end(); ++it)
			if (it->second)
				it->second->sendTextMessage(MSG_ADVANCE, text.c_str());
		std::cout << "[sponsor] " << text << std::endl;
	}

	// Premios del padrino que quedaron pendientes (estaba desconectado cuando el ahijado llegó al hito).
	void deliverSponsor(Player* sponsor)
	{
		bool changed = false;
		for (size_t i = 0; i < links.size(); ++i) {
			Link& link = links[i];
			if (!link.pending || !sameName(link.sponsor, sponsor->getName()))
				continue;
			for (int m = 0; m < MILESTONE_COUNT; ++m) {
				if (!(link.pending & (1 << m)))
					continue;
				const unsigned short gift = levelGiftItemId(sponsor->level);
				giveGold(sponsor, SPONSOR_GOLD[m]);
				giveItem(sponsor, gift, 1);
				std::ostringstream msg;
				msg << "Sponsorship: your recruit " << link.child << " reached level " << MILESTONES[m]
					<< ". You receive " << SPONSOR_GOLD[m] << " gp and " << article(Item::items[gift].name) << ".";
				sponsor->sendTextMessage(MSG_ADVANCE, msg.str().c_str());
			}
			link.pending = 0;
			changed = true;
		}
		if (changed)
			save();
	}

	void showStatus(Player* player)
	{
		std::ostringstream msg;
		Link* mine = findChild(player->getName());
		if (mine) {
			const int next = nextMilestone(mine->done);
			msg << "Your sponsor is " << mine->sponsor << ".";
			if (next >= 0)
				msg << " Your next shared reward is at level " << MILESTONES[next]
					<< " (you: " << CHILD_GOLD[next] << " gp and a gift box).";
			else
				msg << " You have already claimed all milestone rewards.";
			player->sendTextMessage(MSG_INFO, msg.str().c_str());
		}

		std::ostringstream kids;
		size_t n = 0;
		for (size_t i = 0; i < links.size(); ++i) {
			const Link& link = links[i];
			if (!sameName(link.sponsor, player->getName()))
				continue;
			kids << (n ? ", " : "") << link.child << " (level " << link.childLevel;
			const int next = nextMilestone(link.done);
			if (next >= 0)
				kids << ", next reward at " << MILESTONES[next];
			kids << ")";
			++n;
		}
		if (n) {
			std::ostringstream line;
			line << "Your recruits (" << n << "/" << MAX_CHILDREN << "): " << kids.str() << ".";
			player->sendTextMessage(MSG_INFO, line.str().c_str());
		}

		if (!mine && !n) {
			player->sendTextMessage(MSG_INFO,
				"Sponsorship: up to level 15, type !sponsor Name to ask a player of level 30 or higher to "
				"sponsor you; they accept with !sponsor accept YourName. When you reach levels 20, 35, 50, 80 and 100, you both "
				"receive gold and a gift box.");
		}
	}

	void ask(Game* game, Player* child, const std::string& sponsorName)
	{
		if (child->access > 0) {
			child->sendCancel("GMs cannot have a sponsor.");
			return;
		}
		if (Link* mine = findChild(child->getName())) {
			child->sendCancel(("You already have a sponsor: " + mine->sponsor + ".").c_str());
			return;
		}
		if (child->level > CHILD_MAX_LEVEL) {
			child->sendCancel("You can only choose a sponsor up to level 15.");
			return;
		}
		Player* sponsor = game->getPlayerByName(sponsorName);
		if (!sponsor) {
			child->sendCancel((sponsorName + " is offline: they must be online to accept.").c_str());
			return;
		}
		if (sponsor == child || sponsor->getAccount() == child->getAccount()) {
			child->sendCancel("You cannot sponsor yourself or another character on your account.");
			return;
		}
		if (sponsor->access > 0) {
			child->sendCancel("A GM cannot be a sponsor.");
			return;
		}
		if (sponsor->level < SPONSOR_MIN_LEVEL) {
			child->sendCancel("Your sponsor must be level 30 or higher.");
			return;
		}
		if (childCount(sponsor->getName()) >= MAX_CHILDREN) {
			child->sendCancel((sponsor->getName() + " already has 10 recruits.").c_str());
			return;
		}

		for (size_t i = 0; i < requests.size(); ++i) {
			if (sameName(requests[i].child, child->getName())) {
				requests.erase(requests.begin() + i);
				break;
			}
		}
		Request req;
		req.child = child->getName();
		req.sponsor = sponsor->getName();
		req.at = time(NULL);
		requests.push_back(req);

		std::ostringstream toSponsor;
		toSponsor << child->getName() << " (level " << child->level << ") wants you to be their sponsor. "
			<< "Type !sponsor accept " << child->getName() << " within the next 5 minutes.";
		sponsor->sendTextMessage(MSG_ADVANCE, toSponsor.str().c_str());
		child->sendTextMessage(MSG_INFO, ("You asked " + sponsor->getName() +
			" to be your sponsor. They have 5 minutes to accept.").c_str());
	}

	void accept(Game* game, Player* sponsor, const std::string& childName)
	{
		const time_t now = time(NULL);
		int found = -1;
		for (size_t i = 0; i < requests.size(); ++i) {
			if (sameName(requests[i].child, childName) && sameName(requests[i].sponsor, sponsor->getName())
				&& now - requests[i].at <= REQUEST_SECONDS) {
				found = (int)i;
				break;
			}
		}
		if (found < 0) {
			sponsor->sendCancel(("There is no request from " + childName + " (or it expired after 5 minutes).").c_str());
			return;
		}
		requests.erase(requests.begin() + found);

		Player* child = game->getPlayerByName(childName);
		if (!child) {
			sponsor->sendCancel((childName + " is no longer online.").c_str());
			return;
		}
		if (findChild(child->getName())) {
			sponsor->sendCancel((child->getName() + " already has a sponsor.").c_str());
			return;
		}
		if (childCount(sponsor->getName()) >= MAX_CHILDREN) {
			sponsor->sendCancel("You already have 10 recruits.");
			return;
		}

		Link link;
		link.child = child->getName();
		link.sponsor = sponsor->getName();
		link.childLevel = child->level;
		link.done = 0;
		link.pending = 0;
		link.since = (long)now;
		links.push_back(link);
		save();

		giveItem(child, WELCOME_GIFT, 1);
		child->sendTextMessage(MSG_ADVANCE, (sponsor->getName() + " is your sponsor. You receive a novice gift. "
			"You both receive a reward when you reach level 20.").c_str());
		sponsor->sendTextMessage(MSG_ADVANCE, ("You are now the sponsor of " + child->getName() +
			". When they reach levels 20, 35, 50, 80 and 100, you receive gold and a gift box.").c_str());
	}
}

bool Sponsors::Load()
{
	links.clear();
	const std::string filename = fileName();
	std::ifstream probe(filename.c_str());
	if (!probe.good())
		return true;   // todavía no hay padrinos
	probe.close();

	xmlMutexLock(xmlmutex);
	xmlDocPtr doc = xmlParseFile(filename.c_str());
	if (!doc) {
		xmlMutexUnlock(xmlmutex);
		std::cout << "Could not load " << filename << "!" << std::endl;
		return false;
	}
	xmlNodePtr root = xmlDocGetRootElement(doc);
	if (!root || xmlStrcmp(root->name, (const xmlChar*)"sponsors")) {
		xmlFreeDoc(doc);
		xmlMutexUnlock(xmlmutex);
		std::cout << filename << " has an invalid root node." << std::endl;
		return false;
	}
	for (xmlNodePtr node = root->children; node; node = node->next) {
		if (strcmp((const char*)node->name, "link") != 0)
			continue;
		Link link;
		link.child = getProp(node, "child");
		link.sponsor = getProp(node, "sponsor");
		link.childLevel = atoi(getProp(node, "level").c_str());
		link.done = atoi(getProp(node, "done").c_str());
		link.pending = atoi(getProp(node, "pending").c_str());
		link.since = atol(getProp(node, "since").c_str());
		if (!link.child.empty() && !link.sponsor.empty())
			links.push_back(link);
	}
	xmlFreeDoc(doc);
	xmlMutexUnlock(xmlmutex);
	return true;
}

void Sponsors::command(Game* game, Player* player, const std::string& param)
{
	if (!player)
		return;
	const std::string p = trim(param);
	if (p.empty()) {
		deliverSponsor(player);
		showStatus(player);
		return;
	}
	const std::string lp = lower(p);
	if (lp.compare(0, 8, "aceptar ") == 0 || lp.compare(0, 7, "accept ") == 0) {
		accept(game, player, trim(p.substr(p.find(' ') + 1)));
		return;
	}
	ask(game, player, p);
}

void Sponsors::onLevel(Player* player)
{
	Link* link = findChild(player->getName());
	if (!link)
		return;
	link->childLevel = player->level;

	for (int m = 0; m < MILESTONE_COUNT; ++m) {
		const int bit = 1 << m;
		if (player->level < MILESTONES[m] || (link->done & bit))
			continue;
		link->done |= bit;
		link->pending |= bit;

		const unsigned short gift = levelGiftItemId(player->level);
		giveGold(player, CHILD_GOLD[m]);
		giveItem(player, gift, 1);
		std::ostringstream msg;
		msg << "Sponsorship: you reached level " << MILESTONES[m] << ". You receive " << CHILD_GOLD[m]
			<< " gp and " << article(Item::items[gift].name) << "; your sponsor " << link->sponsor << " earns a reward too.";
		player->sendTextMessage(MSG_ADVANCE, msg.str().c_str());

		std::ostringstream all;
		all << player->getName() << ", sponsored by " << link->sponsor << ", reached level " << MILESTONES[m]
			<< ": rewards for both!";
		broadcast(all.str());
	}

	const std::string sponsorName = link->sponsor;   // deliverSponsor puede guardar: no usar link después
	save();
	if (Player* sponsor = g_game.getPlayerByName(sponsorName))
		deliverSponsor(sponsor);
}

void Sponsors::onLogin(Player* player)
{
	if (!player || player->access > 0)
		return;
	deliverSponsor(player);
	if (player->level <= CHILD_MAX_LEVEL && !findChild(player->getName()))
		player->sendTextMessage(MSG_EVENT, "If a friend invited you, type !sponsor Name (level 30 or higher): "
			"you both earn rewards when you reach level milestones.");
}
