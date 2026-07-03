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
#ifdef YUR_READABLES
#include "readables.h"
#include "game.h"
#include "luascript.h"
#include <sstream>
#include <libxml/xmlmemory.h>
#include <libxml/parser.h>

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
// Scrolls escribibles por jugadores (texto compartido y persistente).
// A diferencia de los readables (texto fijo de solo-lectura horneado por
// el staff), esto guarda lo que un jugador escribe en la ventana de texto
// y lo restaura al arrancar, keyeado por la posición del ítem en el mapa.
//////////////////////////////////////////////////////////////////////

// Convierte el literal "\n" (backslash+n) del XML a salto de línea real.
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

// Convierte saltos de línea reales a "\n" para guardarlos en un atributo XML
// (la normalización de atributos de XML colapsaría los newlines a espacios).
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

bool Readables::LoadScrollTexts(Game *game)
{
	std::string file = g_config.getGlobalString("datadir") + "scrolltexts.xml";
	xmlMutexLock(xmlmutex);

	xmlDocPtr doc = xmlParseFile(file.c_str());
	if (!doc)
	{
		// Ausente en el primer arranque: no es error.
		xmlMutexUnlock(xmlmutex);
		return true;
	}

	xmlNodePtr root = xmlDocGetRootElement(doc);
	if (xmlStrcmp(root->name, (const xmlChar*)"scrolltexts"))
	{
		xmlFreeDoc(doc);
		xmlMutexUnlock(xmlmutex);
		return false;
	}

	xmlNodePtr node = root->children;
	while (node)
	{
		if (strcmp((char*) node->name, "scroll") == 0)
		{
			int x = atoi((const char*)xmlGetProp(node, (const xmlChar *) "x"));
			int y = atoi((const char*)xmlGetProp(node, (const xmlChar *) "y"));
			int z = atoi((const char*)xmlGetProp(node, (const xmlChar *) "z"));
			const char* textProp = (const char*)xmlGetProp(node, (const xmlChar *) "text");
			std::string text = textProp ? unescapeScrollText(textProp) : std::string("");

			Tile* tile = game->getTile(x, y, z);
			if (tile)
			{
				Thing* thing = tile->getTopThing();
				Item* item = thing ? dynamic_cast<Item*>(thing) : NULL;
				if (item)
					item->setText(text);
				// Si no hay ítem en el tile, se ignora (el scroll pudo removerse).
			}
		}
		node = node->next;
	}

	xmlFreeDoc(doc);
	xmlMutexUnlock(xmlmutex);
	return true;
}

bool Readables::SaveScrollText(int x, int y, int z, const std::string& text)
{
	std::string file = g_config.getGlobalString("datadir") + "scrolltexts.xml";
	xmlMutexLock(xmlmutex);

	xmlDocPtr doc = xmlParseFile(file.c_str());
	xmlNodePtr root = NULL;
	if (doc)
	{
		root = xmlDocGetRootElement(doc);
		if (xmlStrcmp(root->name, (const xmlChar*)"scrolltexts"))
		{
			xmlFreeDoc(doc);
			doc = NULL;
		}
	}
	if (!doc)
	{
		doc = xmlNewDoc((const xmlChar*)"1.0");
		doc->children = xmlNewDocNode(doc, NULL, (const xmlChar*)"scrolltexts", NULL);
		root = doc->children;
	}

	// Buscar un nodo existente para esta posición (upsert).
	xmlNodePtr found = NULL;
	for (xmlNodePtr node = root->children; node; node = node->next)
	{
		if (strcmp((char*) node->name, "scroll") == 0)
		{
			int nx = atoi((const char*)xmlGetProp(node, (const xmlChar *) "x"));
			int ny = atoi((const char*)xmlGetProp(node, (const xmlChar *) "y"));
			int nz = atoi((const char*)xmlGetProp(node, (const xmlChar *) "z"));
			if (nx == x && ny == y && nz == z)
			{
				found = node;
				break;
			}
		}
	}

	std::stringstream sx, sy, sz;
	sx << x; sy << y; sz << z;
	std::string stored = escapeScrollText(text);

	if (!found)
	{
		found = xmlNewChild(root, NULL, (const xmlChar*)"scroll", NULL);
		xmlSetProp(found, (const xmlChar*)"x", (const xmlChar*)sx.str().c_str());
		xmlSetProp(found, (const xmlChar*)"y", (const xmlChar*)sy.str().c_str());
		xmlSetProp(found, (const xmlChar*)"z", (const xmlChar*)sz.str().c_str());
	}
	xmlSetProp(found, (const xmlChar*)"text", (const xmlChar*)stored.c_str());

	xmlSaveFile(file.c_str(), doc);
	xmlFreeDoc(doc);
	xmlMutexUnlock(xmlmutex);
	return true;
}
#endif //YUR_READABLES
