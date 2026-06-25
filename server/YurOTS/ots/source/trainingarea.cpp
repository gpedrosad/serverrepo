//////////////////////////////////////////////////////////////////////
// OpenTibia - an opensource roleplaying game
//////////////////////////////////////////////////////////////////////
// Training area by Yurez
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
#ifdef YUR_TRAINING_AREA
#include "trainingarea.h"
#include "game.h"
#include "luascript.h"
#include <libxml/xmlmemory.h>
#include <libxml/parser.h>

extern LuaScript g_config;


bool TrainingArea::Load(Game* game)
{
	std::string file = g_config.DATA_DIR + "trainingareas.xml";
	xmlDocPtr doc;

	doc = xmlParseFile(file.c_str());
	if (!doc)
		return false;

	Position pos, exit;
	xmlNodePtr root, tileNode, areaNode;

	root = xmlDocGetRootElement(doc);
	if (xmlStrcmp(root->name, (const xmlChar*)"trainingareas"))
	{
		xmlFreeDoc(doc);
		return false;
	}

	areaNode = root->children;
	while (areaNode)
	{
		if (strcmp((char*) areaNode->name, "trainingarea") == 0)
		{
			exit.x = atoi((const char*)xmlGetProp(areaNode, (const xmlChar *) "exitx"));
			exit.y = atoi((const char*)xmlGetProp(areaNode, (const xmlChar *) "exity"));
			exit.z = atoi((const char*)xmlGetProp(areaNode, (const xmlChar *) "exitz"));

			tileNode = areaNode->children;
			while (tileNode)
			{
				if (strcmp((char*) tileNode->name, "tile") == 0)
				{
					pos.x = atoi((const char*)xmlGetProp(tileNode, (const xmlChar *) "x"));
					pos.y = atoi((const char*)xmlGetProp(tileNode, (const xmlChar *) "y"));
					pos.z = atoi((const char*)xmlGetProp(tileNode, (const xmlChar *) "z"));

					if (!AddTrainingTile(game, pos, exit))
					{
						xmlFreeDoc(doc);
						return false;
					}
				}
				else if (strcmp((const char*) tileNode->name, "tiles") == 0)
				{
					int fromx = atoi((const char*) xmlGetProp(tileNode, (const xmlChar*) "fromx"));
					int fromy = atoi((const char*) xmlGetProp(tileNode, (const xmlChar*) "fromy"));
					int fromz = atoi((const char*) xmlGetProp(tileNode, (const xmlChar*) "fromz"));
					int tox = atoi((const char*) xmlGetProp(tileNode, (const xmlChar*) "tox"));
					int toy = atoi((const char*) xmlGetProp(tileNode, (const xmlChar*) "toy"));
					int toz = atoi((const char*) xmlGetProp(tileNode, (const xmlChar*) "toz"));

					if (fromx > tox) std::swap(fromx, tox);
					if (fromy > toy) std::swap(fromy, toy);
					if (fromz > toz) std::swap(fromz, toz);

					for (int x = fromx; x <= tox; x++)
						for (int y = fromy; y <= toy; y++)
							for (int z = fromz; z <= toz; z++)
								if (!AddTrainingTile(game, Position(x,y,z), exit))
								{
									xmlFreeDoc(doc);
									return false;
								}
				}
				tileNode = tileNode->next;
			}
		}
		areaNode = areaNode->next;
	}

	xmlFreeDoc(doc);
	return true;
}

bool TrainingArea::AddTrainingTile(Game* game, const Position& pos, const Position& exit)
{
	Tile* tile = game->getTile(pos);
	if (!tile)
	{
		std::cout << "\nTile " << pos << " is not valid!";
		return false;
	}

	if (tile->isTrainingArea())
	{
		std::cout << "\nTile " << pos << " is already assigned to training area!";
		return false;
	}

	tile->setTrainingArea(exit);
	return true;
}
#endif //YUR_TRAINING_AREA
