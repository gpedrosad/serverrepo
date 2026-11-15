//////////////////////////////////////////////////////////////////////
// OpenTibia - an opensource roleplaying game
//////////////////////////////////////////////////////////////////////
// Readables by Yurez
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
#include "readables.h"
#include "game.h"
#include "luascript.h"
#include <libxml/xmlmemory.h>
#include <libxml/parser.h>
#include <sstream>
#include <fstream>

extern LuaScript g_config;
extern xmlMutexPtr xmlmutex;

bool Readables::Load(Game *game)
{
	std::string file = g_config.getGlobalString("datadir") + "readables.xml";
	xmlDocPtr doc;
	xmlMutexLock(xmlmutex);

	doc = xmlParseFile(file.c_str());
	if (!doc)
		return false;

	xmlNodePtr root, readableNode;
	root = xmlDocGetRootElement(doc);
	if (xmlStrcmp(root->name, (const xmlChar*)"readables"))
	{
		xmlFreeDoc(doc);
		xmlMutexUnlock(xmlmutex);
		return false;
	}

	readableNode = root->children;
	while (readableNode)
	{
		if (strcmp((char*) readableNode->name, "readable") == 0)
		{
			int x = atoi((const char*)xmlGetProp(readableNode, (const xmlChar *) "x"));
			int y = atoi((const char*)xmlGetProp(readableNode, (const xmlChar *) "y"));
			int z = atoi((const char*)xmlGetProp(readableNode, (const xmlChar *) "z"));
			std::string text = (const char*)xmlGetProp(readableNode, (const xmlChar *) "text");

			for (size_t i = 0; i < text.length()-1; i++)	// make real newlines
				if (text.at(i) == '\\' && text.at(i+1) == 'n')
				{
					text[i] = ' ';
					text[i+1] = '\n';
				}

			Tile* tile = game->getTile(x, y, z);
			if (tile)
			{
				Thing* thing = tile->getTopThing();
				Item* item = thing? dynamic_cast<Item*>(thing) : NULL;

				if (item)
					item->setReadable(text);
				else
				{
					std::cout << "\nTop thing at " << Position(x,y,z) << " is not an item!";
					return false;
				}
			}
			else
			{
				std::cout << "\nTile " << Position(x,y,z) << " is not valid!";
				return false;
			}
		}
		readableNode = readableNode->next;
	}

	xmlFreeDoc(doc);
	xmlMutexUnlock(xmlmutex);
	return true;
}

//////////////////////////////////////////////////////////////////////
// Scrolls escribibles del piso (portado de feat/readables-writeables-build-fix, jul 2026)
//////////////////////////////////////////////////////////////////////

// libxml avisa por consola si el archivo no está; scrolltexts.xml no existe hasta que alguien escribe.
static xmlDocPtr parseIfExists(const std::string& file)
{
	std::ifstream probe(file.c_str());
	return probe.good() ? xmlParseFile(file.c_str()) : NULL;
}

static std::string scrollProp(xmlNodePtr node, const char* name)
{
	xmlChar* value = xmlGetProp(node, (const xmlChar*)name);
	if (!value)
		return std::string();
	std::string out = (const char*)value;
	xmlFree(value);
	return out;
}

// En el atributo XML los saltos de línea se guardan como "\\n" (la normalización de atributos los
// convertiría en espacios).
static std::string escapeScrollText(const std::string& in)
{
	std::string out;
	for (size_t i = 0; i < in.length(); i++)
	{
		if (in[i] == '\n')
			out += "\\n";
		else
			out += in[i];
	}
	return out;
}

static std::string unescapeScrollText(const std::string& in)
{
	std::string out;
	for (size_t i = 0; i < in.length(); i++)
	{
		if (in[i] == '\\' && i + 1 < in.length() && in[i+1] == 'n')
		{
			out += '\n';
			i++;
		}
		else
			out += in[i];
	}
	return out;
}

bool Readables::LoadScrollTexts(Game *game)
{
	std::string file = g_config.getGlobalString("datadir") + "scrolltexts.xml";
	xmlMutexLock(xmlmutex);
	xmlDocPtr doc = parseIfExists(file);
	if (!doc)	// no existe hasta que alguien escribe algo
	{
		xmlMutexUnlock(xmlmutex);
		return true;
	}

	xmlNodePtr root = xmlDocGetRootElement(doc);
	if (!root || xmlStrcmp(root->name, (const xmlChar*)"scrolltexts"))
	{
		xmlFreeDoc(doc);
		xmlMutexUnlock(xmlmutex);
		return false;
	}

	for (xmlNodePtr node = root->children; node; node = node->next)
	{
		if (strcmp((const char*)node->name, "scroll") != 0)
			continue;
		int x = atoi(scrollProp(node, "x").c_str());
		int y = atoi(scrollProp(node, "y").c_str());
		int z = atoi(scrollProp(node, "z").c_str());
		Tile* tile = game->getTile(x, y, z);
		Thing* thing = tile ? tile->getTopThing() : NULL;
		Item* item = thing ? dynamic_cast<Item*>(thing) : NULL;
		// Solo si arriba sigue habiendo algo escribible: si el scroll ya no está, el texto no se le
		// pega a otro ítem del tile.
		if (item && (item->getRWInfo() & CAN_BE_WRITTEN))
			item->setText(unescapeScrollText(scrollProp(node, "text")));
	}

	xmlFreeDoc(doc);
	xmlMutexUnlock(xmlmutex);
	return true;
}

bool Readables::SaveScrollText(int x, int y, int z, const std::string& text)
{
	std::string file = g_config.getGlobalString("datadir") + "scrolltexts.xml";
	xmlMutexLock(xmlmutex);

	xmlDocPtr doc = parseIfExists(file);
	xmlNodePtr root = doc ? xmlDocGetRootElement(doc) : NULL;
	if (doc && (!root || xmlStrcmp(root->name, (const xmlChar*)"scrolltexts")))
	{
		xmlFreeDoc(doc);
		doc = NULL;
	}
	if (!doc)
	{
		doc = xmlNewDoc((const xmlChar*)"1.0");
		root = xmlNewDocNode(doc, NULL, (const xmlChar*)"scrolltexts", NULL);
		xmlDocSetRootElement(doc, root);
	}

	std::stringstream sx, sy, sz;
	sx << x; sy << y; sz << z;

	xmlNodePtr found = NULL;
	for (xmlNodePtr node = root->children; node && !found; node = node->next)
	{
		if (strcmp((const char*)node->name, "scroll") == 0 && scrollProp(node, "x") == sx.str() &&
			scrollProp(node, "y") == sy.str() && scrollProp(node, "z") == sz.str())
			found = node;
	}
	if (!found)
	{
		found = xmlNewChild(root, NULL, (const xmlChar*)"scroll", NULL);
		xmlSetProp(found, (const xmlChar*)"x", (const xmlChar*)sx.str().c_str());
		xmlSetProp(found, (const xmlChar*)"y", (const xmlChar*)sy.str().c_str());
		xmlSetProp(found, (const xmlChar*)"z", (const xmlChar*)sz.str().c_str());
	}
	xmlSetProp(found, (const xmlChar*)"text", (const xmlChar*)escapeScrollText(text).c_str());

	bool ok = xmlSaveFile(file.c_str(), doc) >= 0;
	xmlFreeDoc(doc);
	xmlMutexUnlock(xmlmutex);
	return ok;
}
