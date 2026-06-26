//////////////////////////////////////////////////////////////////////
// OpenTibia - an opensource roleplaying game
//////////////////////////////////////////////////////////////////////
// Base class for the Account Loader/Saver
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

#include "ioplayer.h"

#include <algorithm>
#include <fstream>
#include <cctype>

#ifndef WIN32
#include <dirent.h>
#include <unistd.h>
#endif

#ifdef __USE_MYSQL__
	#include "ioplayersql.h"
#endif
#include "ioplayerxml.h"

#ifdef __USE_MYSQL__
#include "luascript.h"
extern LuaScript g_config;
#endif

IOPlayer* IOPlayer::_instance = NULL;

IOPlayer* IOPlayer::instance(){
	if(!_instance){
#ifdef __USE_MYSQL__
        if(g_config.getGlobalString("sourcedata") == "SQL") 
		_instance = (IOPlayer*)new IOPlayerSQL;
		else // if(g_config.getGlobalString("sourcedata") == "XML") //fallback to xml
#endif
		_instance = (IOPlayer*)new IOPlayerXML;

	}
    #ifdef __DEBUG__
	printf("%s \n", _instance->getSourceDescription());
	#endif 
	return _instance;
}

std::string IOPlayer::playerFilePath(const std::string& datadir, const std::string& name)
{
	std::string filename = datadir + "players/" + name + ".xml";
	std::transform(filename.begin(), filename.end(), filename.begin(),
		[](unsigned char c){ return (char)std::tolower(c); });
	return filename;
}

bool IOPlayer::playerFileExists(const std::string& datadir, const std::string& name)
{
	std::ifstream file(playerFilePath(datadir, name).c_str());
	return file.good();
}

void IOPlayer::normalizePlayerFilenames(const std::string& datadir)
{
#ifndef WIN32
	std::string dirpath = datadir + "players/";
	DIR* dir = opendir(dirpath.c_str());
	if(!dir)
		return;

	struct dirent* ent;
	while((ent = readdir(dir)) != NULL) {
		std::string fname = ent->d_name;
		if(fname.length() < 5 || fname.compare(fname.length() - 4, 4, ".xml") != 0)
			continue;

		std::string stem = fname.substr(0, fname.length() - 4);
		if(stem.length() == 1 && stem[0] >= '0' && stem[0] <= '4')
			continue;

		std::string lower = stem;
		std::transform(lower.begin(), lower.end(), lower.begin(),
			[](unsigned char c){ return (char)std::tolower(c); });
		if(stem == lower)
			continue;

		std::string from = dirpath + fname;
		std::string to = dirpath + lower + ".xml";
		if(access(to.c_str(), F_OK) == 0) {
			std::cout << ":: Warning: player filename conflict " << fname << " / " << lower << ".xml" << std::endl;
			continue;
		}

		if(rename(from.c_str(), to.c_str()) == 0)
			std::cout << ":: Renamed player file " << fname << " -> " << lower << ".xml" << std::endl;
	}
	closedir(dir);
#endif //WIN32
}

bool IOPlayer::loadPlayer(Player* player, std::string name){
	return false;
}

bool IOPlayer::savePlayer(Player* player){
	return false;
}

bool IOPlayer::getGuidByName(unsigned long &guid, unsigned long &alvl, std::string &name)
{
	return false;
}

bool IOPlayer::getNameByGuid(unsigned long guid, std::string &name)
{
	return false;
}
