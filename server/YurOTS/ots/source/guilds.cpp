//////////////////////////////////////////////////////////////////////
// OpenTibia - an opensource roleplaying game
//////////////////////////////////////////////////////////////////////
// Guilds by Yurez
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
#ifdef YUR_GUILD_SYSTEM
#include "guilds.h"
#include "player.h"
#include "luascript.h"
#include <algorithm>
#include <locale>
#include <cctype>

extern LuaScript g_config;
extern xmlMutexPtr xmlmutex;
std::vector<Guilds::Guild*> Guilds::guilds;
unsigned long Guilds::Guild::counter = 0x10;

// Player names are compared case-insensitively: the Guild Master NPC sees the text the player
// typed ("bob"), while the real name is "Bob". Before, invite/join/kick silently failed.
static bool sameName(const std::string& a, const std::string& b)
{
	if(a.size() != b.size())
		return false;
	for(size_t i = 0; i < a.size(); i++)
		if(tolower((unsigned char)a[i]) != tolower((unsigned char)b[i]))
			return false;
	return true;
}

Guilds::Guild::Guild(std::string name)
{
	gid = counter++;
	gname = name;
}

void Guilds::Guild::addMember(std::string name, gstat_t status, std::string rank, std::string nick)
{
	Member m = { status, name, rank, nick };
	members.push_back(m);
}

std::string Guilds::Guild::getName() const
{
	return gname;
}

gstat_t Guilds::Guild::getGuildStatus(std::string name) const
{
	for (size_t i = 0; i < members.size(); i++)
		if (sameName(members[i].name, name))
			return members[i].status;
	return GUILD_NONE;
}

bool Guilds::Guild::setGuildStatus(std::string name, gstat_t status)
{
	for (size_t i = 0; i < members.size(); i++)
		if (sameName(members[i].name, name))
		{
			members[i].status = status;
			return true;
		}
	return false;
}

void Guilds::Guild::setGuildInfo(std::string name, gstat_t status, std::string rank)
{
	for (size_t i = 0; i < members.size(); i++)
		if (sameName(members[i].name, name))
		{
			members[i].status = status;
			members[i].rank = rank;
			return;
		}

	addMember(name, status, rank, "");
}

bool Guilds::Guild::clearGuildInfo(std::string name)
{
	for (size_t i = 0; i < members.size(); i++)
		if (sameName(members[i].name, name))
		{
			members.erase(members.begin()+i);
			return true;
		}
	return false;
}

bool Guilds::Guild::setGuildNick(std::string name, std::string nick)
{
	for (size_t i = 0; i < members.size(); i++)
		if (sameName(members[i].name, name))
		{
			members[i].nick = nick;
			return true;
		}
	return false;
}

bool Guilds::Guild::isEmpty() const
{
	return members.empty();
}

bool Guilds::Guild::reloadGuildInfo(Player* player)
{
	std::string name = player->getName();
	for (size_t i = 0; i < members.size(); i++)
		if (sameName(members[i].name, name))
		{
			player->setGuildInfo(members[i].status, gid, gname, members[i].rank, members[i].nick);
			return true;
		}
	return false;
}

void Guilds::Guild::save(xmlNodePtr guildNode)
{
	xmlNodePtr memberNode;

	for (size_t i = 0; i < members.size(); i++)
	{
		memberNode = xmlNewNode(NULL, (const xmlChar*)"member");
		xmlSetProp(memberNode, (const xmlChar*) "status", (const xmlChar*)str(members[i].status).c_str());
		xmlSetProp(memberNode, (const xmlChar*) "name", (const xmlChar*)members[i].name.c_str());
		xmlSetProp(memberNode, (const xmlChar*) "rank", (const xmlChar*)members[i].rank.c_str());
		xmlSetProp(memberNode, (const xmlChar*) "nick", (const xmlChar*)members[i].nick.c_str());
		xmlAddChild(guildNode, memberNode);
	}
}

bool Guilds::Load()
{
	std::string file = g_config.getGlobalString("datadir") + "guilds.xml";
	xmlDocPtr doc;
	xmlMutexLock(xmlmutex);

	doc = xmlParseFile(file.c_str());
	if (!doc)
		return false;

	xmlNodePtr root, guildNode, memberNode;
	root = xmlDocGetRootElement(doc);
	if (xmlStrcmp(root->name, (const xmlChar*)"guilds")) 
	{
		xmlFreeDoc(doc);
		xmlMutexUnlock(xmlmutex);
		return false;
	}

	guildNode = root->children;
	while (guildNode)
	{
		if (strcmp((char*) guildNode->name, "guild") == 0)
		{
			std::string name = (const char*)xmlGetProp(guildNode, (const xmlChar *) "name");
			Guild* guild = new Guild(name);

			memberNode = guildNode->children;
			while (memberNode)
			{
				if (strcmp((char*) memberNode->name, "member") == 0)
				{
					gstat_t status = (gstat_t)atoi((const char*)xmlGetProp(memberNode, (const xmlChar *) "status"));
					std::string name = (const char*)xmlGetProp(memberNode, (const xmlChar *) "name");
					std::string rank = (const char*)xmlGetProp(memberNode, (const xmlChar *) "rank");

					std::string nick;
					const char* tmp = (const char*)xmlGetProp(memberNode, (const xmlChar *) "nick");
					if (tmp)
						nick = std::string(tmp);
					else
						nick = (const char*)xmlGetProp(memberNode, (const xmlChar *) "title");	// old
					
					guild->addMember(name, status, rank, nick);
				}
				memberNode = memberNode->next;
			}

			guilds.push_back(guild);
		}
		guildNode = guildNode->next;
	}

	xmlFreeDoc(doc);
	xmlMutexUnlock(xmlmutex);
	return true;	
}

bool Guilds::Save()
{
	std::string file = g_config.getGlobalString("datadir") + "guilds.xml";
	xmlDocPtr doc;
	xmlMutexLock(xmlmutex);

	xmlNodePtr root, guildNode;
	doc = xmlNewDoc((const xmlChar*)"1.0");

	doc->children = xmlNewDocNode(doc, NULL, (const xmlChar*)"guilds", NULL);
    root = doc->children;

	for (size_t i = 0; i < guilds.size(); i++)
	{
		guildNode = xmlNewNode(NULL, (const xmlChar*)"guild");
		xmlSetProp(guildNode, (const xmlChar*) "name", (const xmlChar*)guilds[i]->getName().c_str());
		guilds[i]->save(guildNode);
		xmlAddChild(root, guildNode);
	}

	if (xmlSaveFile(file.c_str(), doc))
	{
		xmlFreeDoc(doc);
		xmlMutexUnlock(xmlmutex);
		return true;
	}
	else
	{
		xmlFreeDoc(doc);
		xmlMutexUnlock(xmlmutex);
		std::cout << "Failed to save " << file << std::endl;
		return false;
	}
}

bool Guilds::AddNewGuild(std::string gname)
{
	for (size_t i = 0; i < guilds.size(); i++)
		if (sameName(guilds[i]->getName(), gname))
			return false;

	guilds.push_back(new Guild(gname));
	return true;
}

// These are only called from the Guild Master NPC (Lua). They used to throw std::runtime_error,
// which unwinds through the Lua C code and can take the server down; now a miss does nothing.
void Guilds::DeleteGuild(std::string gname)
{
	for (size_t i = 0; i < guilds.size(); i++)
		if (guilds[i]->getName() == gname)
		{
			delete guilds[i];
			guilds.erase(guilds.begin()+i);
			return;
		}
}

std::string Guilds::GetGuildName(std::string name)
{
	for (size_t i = 0; i < guilds.size(); i++)
		if (guilds[i]->getGuildStatus(name) != GUILD_NONE)
			return guilds[i]->getName();
	return "";
}

gstat_t Guilds::GetGuildStatus(std::string name)
{
	gstat_t status = GUILD_NONE;
	for (size_t i = 0; i < guilds.size(); i++)
		if ((status = guilds[i]->getGuildStatus(name)) != GUILD_NONE)
			break;
	return status;
}

void Guilds::SetGuildStatus(std::string name, gstat_t status)
{
	for (size_t i = 0; i < guilds.size(); i++)
		if (guilds[i]->setGuildStatus(name, status))
			return;
}

// A player belongs to at most one guild: an invited player who founds a guild or gets invited
// somewhere else leaves the old entry first (before, both entries stayed in guilds.xml).
void Guilds::SetGuildInfo(std::string name, gstat_t status, std::string rank, std::string gname)
{
	Guild* target = NULL;
	for (size_t i = 0; i < guilds.size(); i++)
		if (guilds[i]->getName() == gname)
			target = guilds[i];
	if (!target)
		return;

	if (target->getGuildStatus(name) == GUILD_NONE)
		ClearGuildInfo(name);
	target->setGuildInfo(name, status, rank);
}

// Removes the player from their guild; a guild left without members is deleted.
void Guilds::ClearGuildInfo(std::string name)
{
	for (size_t i = 0; i < guilds.size(); i++)
		if (guilds[i]->clearGuildInfo(name))
		{
			if (guilds[i]->isEmpty())
			{
				delete guilds[i];
				guilds.erase(guilds.begin()+i);
			}
			return;
		}
}

void Guilds::SetGuildNick(std::string name, std::string nick)
{
	for (size_t i = 0; i < guilds.size(); i++)
		if (guilds[i]->setGuildNick(name, nick))
			return;
}

void Guilds::ReloadGuildInfo(Player* player)
{
	for (size_t i = 0; i < guilds.size(); i++)
		if (guilds[i]->reloadGuildInfo(player))
			return;

	player->setGuildInfo(GUILD_NONE, 0, "", "", "");
}
#endif //YUR_GUILD_SYSTEM
