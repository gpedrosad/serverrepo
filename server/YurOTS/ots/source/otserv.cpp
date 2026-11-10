//////////////////////////////////////////////////////////////////////
// OpenTibia - an opensource roleplaying game
//////////////////////////////////////////////////////////////////////
// otserv main. The only place where things get instantiated.
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

#include <string>
#include <iostream>
#include <iomanip>
#include <fstream>
#include <sstream>
#include <ctime>

#include "otsystem.h"
#include "networkmessage.h"
#include "protocol76.h"

#include <stdlib.h>
#include <time.h>
#include "game.h"

#include "ioaccount.h"
#include "ioplayer.h"

#include "status.h"
#include "spells.h"
#include "monsters.h"
#include "actions.h"
#include "commands.h"

#include "luascript.h"
#include "account.h"

#include "tools.h"
#include "md5.h"

#include "summons.h"
#include "pvparena.h"
#include "trainingarea.h"
#include "readables.h"
#include "private_trainers.h"
#include "aac.h"

	#include <fcntl.h>
	#include <arpa/inet.h>
	#include <signal.h>
	#include <errno.h>

	#define SOCKET_ERROR -1
	#define ERROR_EINTR EINTR

	/* Comment below line if you want to execute otserv with root user (NOT RECOMMENDED) */
	/* #define _NO_ROOT_PERMISSION_ */
	/* #define _HOMEDIR_CONF_ */

	extern int errno; 

#ifdef __DEBUG_CRITICALSECTION__
OTSYS_THREAD_LOCK_CLASS::LogList OTSYS_THREAD_LOCK_CLASS::loglist;
#endif

std::vector< std::pair<unsigned long, unsigned long> > serverIPs;
std::vector< std::pair<unsigned long, unsigned long> > bannedIPs;

LuaScript g_config;

Items Item::items;
ReverseItemMap Items::revItems;
Game g_game;
Spells spells(&g_game);
Actions actions(&g_game);
Commands commands(&g_game);
Monsters g_monsters;

#include "crashhandler.h"
#include "networkmessage.h"
#include "socket_debug.h"

enum passwordType_t{
	PASSWORD_TYPE_PLAIN,
	PASSWORD_TYPE_MD5,
};

passwordType_t passwordType;

static in_addr_t resolveHostToIPv4(const std::string& host)
{
	in_addr_t addr = inet_addr(host.c_str());
	if (addr != INADDR_NONE)
		return addr;

	hostent *he = gethostbyname(host.c_str());
	if (he != NULL && he->h_addr_list != NULL && he->h_addr_list[0] != NULL)
		return *(in_addr_t*)he->h_addr_list[0];

	std::cout << "WARNING: Could not resolve IP host \"" << host << "\", using 127.0.0.1" << std::endl;
	return inet_addr("127.0.0.1");
}

bool passwordTest(std::string &plain, std::string &hash)
{
	if(passwordType == PASSWORD_TYPE_MD5){
		MD5_CTX m_md5;
		std::stringstream hexStream;
		std::string plainHash;

		MD5Init(&m_md5, 0);
		MD5Update(&m_md5, (const unsigned char*)plain.c_str(), (unsigned int)plain.length());
		MD5Final(&m_md5);

		hexStream.flags(std::ios::hex);
		for(int i=0;i<16;i++){
			hexStream << std::setw(2) << std::setfill('0') << (unsigned long)m_md5.digest[i];
		}

		plainHash = hexStream.str();
		std::transform(plainHash.begin(), plainHash.end(), plainHash.begin(), upchar);
		std::transform(hash.begin(), hash.end(), hash.begin(), upchar);
		if(plainHash == hash){
			return true;
		}
		else{
			return false;
		}
	}
	else{
		if(plain == hash){
			return true;
		}
		else{
			return false;
		}

	}

}

bool isclientBanished(SOCKET s)
{
	sockaddr_in sain;
	socklen_t salen = sizeof(sockaddr_in);

	if (getpeername(s, (sockaddr*)&sain, &salen) == 0)
	{
		unsigned long clientip = *(unsigned long*)&sain.sin_addr;

		for (size_t i = 0; i < bannedIPs.size(); ++i) {
      if ((bannedIPs[i].first & bannedIPs[i].second) == (clientip & bannedIPs[i].second))
				return true;
		}
	}

	return false;
}

std::string MakeRejectMessage(int place)
{
	if (place < 0)
		return std::string("Wrong temple position!");
	else
	{
		std::ostringstream msg;
		msg << "Too many Players online.\n";

		if (!g_config.QUEUE_PREMMY)
			msg << "Only premium players are allowed to enter.\n";

		msg << "\nYou are at place " << place << " on the waiting list.";
		return msg.str();
	}
}

OTSYS_THREAD_RETURN ConnectionHandler(void *dat)
{

	srand((unsigned)time(NULL));

	SOCKET* sockptr = (SOCKET*)dat;
	SOCKET s = *sockptr;
	delete sockptr;

	socketDebugLog("accept " + socketDescribeState(s) + " peer=" + socketPeerIp(s));

	setSocketHandshakeRecvTimeout(s);

	NetworkMessage msg;
	if (msg.ReadFromSocket(s))
	{
		// Quitar timeout de handshake en cuanto llega el primer paquete.
		setSocketGameRecvBlocking(s);

		unsigned short protId = msg.GetU16();
		{
			std::ostringstream oss;
			oss << "first packet protId=0x" << std::hex << protId << std::dec
			    << " " << socketDescribeState(s);
			socketDebugLog(oss.str());
		}

		// login server connection
		if (protId == 0x0201)
		{
			msg.SkipBytes(15);
			unsigned int accnumber = msg.GetU32();
			std::string  password  = msg.GetString();

			int serverip = resolveHostToIPv4(g_config.getGlobalString("ip", "127.0.0.1"));

			msg.Reset();

			if(isclientBanished(s)) {
				msg.AddByte(0x0A);
				msg.AddString("Your IP is banished!");
			}
			else {

				Account account = IOAccount::instance()->loadAccount(accnumber);
				if (account.accnumber == accnumber && passwordTest(password,account.password)) // seems to be a successful load
				{
					msg.AddByte(0x14);
					std::stringstream motd;
					motd << g_config.getGlobalString("motdnum");
					motd << "\n";
					motd << g_config.getGlobalString("motd");
					msg.AddString(motd.str());

					msg.AddByte(0x64);
					msg.AddByte((uint8_t)account.charList.size());

					std::list<std::string>::iterator it;
					for (it = account.charList.begin(); it != account.charList.end(); it++)
					{
						msg.AddString((*it));
						msg.AddString(g_config.getGlobalString("worldname","YurOTS"));
						msg.AddU32(serverip);
						msg.AddU16(atoi(g_config.getGlobalString("port").c_str()));
					}

					msg.AddU16(account.premDays);
				}
				else
				{
					msg.AddByte(0x0A);
					msg.AddString("Please enter a valid account number and password.");
				}
			}

			msg.WriteToSocket(s);
		}
		// gameworld connection tibia 7.6
		else if (protId == 0x020A)
		{
			unsigned char  clientos = msg.GetByte();
			unsigned short version  = msg.GetU16();
			unsigned char  unknown = msg.GetByte();
			unsigned long accnumber = msg.GetU32();
			std::string name     = msg.GetString();
			std::string password = msg.GetString();

			if(version != 760){
				msg.Reset();
				msg.AddByte(0x14);
				msg.AddString("Only clients with protocol 7.6 allowed!");
				msg.WriteToSocket(s);
			}
			else if(isclientBanished(s)){
				msg.Reset();
				msg.AddByte(0x14);
				msg.AddString("Your IP is banished!");
				msg.WriteToSocket(s);
			}
			else{
				OTSYS_SLEEP(1000);
				std::string acc_pass;
				if(IOAccount::instance()->getPassword(accnumber, name, acc_pass) && passwordTest(password,acc_pass))
				{
					bool isLocked = true;
					OTSYS_THREAD_LOCK(g_game.gameLock, "ConnectionHandler()")
					Player* player = g_game.getPlayerByName(name);
					bool playerexist = (player != NULL);
					const bool allowClones = (g_config.getGlobalNumber("allowclones", 0) != 0);
					const bool replaceConnectedCharacter = (g_config.getGlobalNumber("replaceconnectedcharacter", 1) != 0);
					if(player){
						//reattach player?
						if(player->client->s == 0 && player->isRemoved == false && !allowClones){
							player->lastlogin = std::time(NULL);
							player->client->reinitializeProtocol();
							setSocketGameRecvBlocking(s);
							player->client->s = s;
							socketDebugLog("reattach player=" + name + " " + socketDescribeState(s));
							player->client->sendThingAppear(player);
							player->lastip = player->getIP();
							s = 0;
						}
						// If the character is still online, replace the old session instead of
						// rejecting the new login. We remove/save the existing player first and
						// then shut down the old socket so its ReceiveLoop can terminate cleanly.
						else if(player->client && player->client->s != 0 && player->isRemoved == false &&
							!allowClones && replaceConnectedCharacter){
							std::cout << "Replacing active session for player: " << name << std::endl;
							player->client->logout();
							player->client->disconnectConnection();
							playerexist = (g_game.getPlayerByName(name) != NULL);
						}

						//guess not...
						player = NULL;
					}

					//OTSYS_THREAD_UNLOCK(g_game.gameLock, "ConnectionHandler()")

					if(s){
						Protocol76* protocol;
						protocol = new Protocol76(s);
						player = new Player(name, protocol);
						player->useThing();
						player->setID();
						IOPlayer::instance()->loadPlayer(player, name);
						int placeInQueue = -1;
						static const int ACCESS_ENTER = g_config.getGlobalNumber("accessenter",3);

						if(playerexist && !allowClones){
							std::cout << "reject player... (already logged in)" << std::endl;
							msg.Reset();
							msg.AddByte(0x14);
							msg.AddString("You are already logged in.");
							msg.WriteToSocket(s);
						}
						else if (player->banned)
						{
							msg.Reset();
							msg.AddByte(0x14);
							msg.AddString("Your character has been banished!");
							msg.WriteToSocket(s);
						}
						else if(g_game.getGameState() == GAME_STATE_SHUTDOWN){
							//nothing to do
						}
						else if(g_game.getGameState() == GAME_STATE_CLOSED && player->access < ACCESS_ENTER){
							msg.Reset();
							msg.AddByte(0x14);
							msg.AddString("Server temporarly closed.");
							msg.WriteToSocket(s);
						}
						else if (!protocol->ConnectPlayer(&placeInQueue)) {
							Status* stat = Status::instance();
							stat->playerswaiting = (int)g_game.loginQueue.size();
							if (placeInQueue < 0)
								std::cout << "reject player... wrong temple position" << std::endl;
							else
								std::cout << "reject player... place in queue: " << placeInQueue << std::endl;
							msg.Reset();
							msg.AddByte(0x16);
							msg.AddString(MakeRejectMessage(placeInQueue));
							msg.AddByte(30);
							msg.WriteToSocket(s);
						}
						else{
							Status* stat = Status::instance();
							stat->addPlayer();
							g_game.writeOnlineList();
							player->lastlogin = std::time(NULL);
							player->lastip = player->getIP();
							setSocketGameRecvBlocking(s);
							socketDebugLog("game login ok player=" + name + " entering ReceiveLoop " + socketDescribeState(s));
							s = 0;            // protocol/player will close socket

							OTSYS_THREAD_UNLOCK(g_game.gameLock, "ConnectionHandler()")
							isLocked = false;

							protocol->ReceiveLoop();
							stat->removePlayer();
							g_game.writeOnlineList();
						}

						if(player){
							g_game.FreeThing(player);
						}
					}

					if(isLocked){
						OTSYS_THREAD_UNLOCK(g_game.gameLock, "ConnectionHandler()")
					}
				}
				else{
					msg.Reset();
					msg.AddByte(0x14);
					msg.AddString("Please enter a valid account number and password.");
					msg.WriteToSocket(s);
				}
			}
		}
		// Since Cip made 02xx as Tibia protocol,
		// Lets make FFxx as "our great info protocol" ;P
		else if (protId == 0xFFFF) {
			if (msg.GetRaw() == "info"){
				Status* status = Status::instance();

				uint64_t running = (OTSYS_TIME() - status->start)/1000;
				#ifdef __DEBUG__
				std::cout << ":: Uptime: " << running << std::endl;
				#endif
				std::string str = status->getStatusString();
				send(s, str.c_str(), (int)str.size(), 0);
				shutdown(s, SHUT_RDWR);
			}
		}
		// Another ServerInfo protocol
		// Starting from 01, so the above could be 00 ;)
		else if (protId == 0xFF01) {
			// This one doesn't need to read nothing, so we could save time and bandwidth
			// Can be called thgough a program that understand the NetMsg protocol
			Status* status = Status::instance();
			status->getInfo(msg);
			msg.WriteToSocket(s);
		}
		else if (protId == 0xFFAC) 
		{
			std::string response = AccountCreator::process(msg.GetRaw());
			msg.Reset();
			msg.AddString(response);
			msg.WriteToSocket(s);
		}
  }
  else{
		socketDebugLog(
			std::string("handshake read failed peer=") + socketPeerIp(s) +
			" reason=" + (msg.getLastReadFailReason()[0] ? msg.getLastReadFailReason() : "?") +
			" errno=" + std::to_string(msg.getLastReadErrno()));
  }
  if(s)
	  closesocket(s);

  return 0;
}

void ErrorMessage(const char* message) {
  std::cout << std::endl << std::endl << "Error: " << message;

  std::string s;
  std::cin >> s;
}

extern volatile sig_atomic_t g_yurotsWantShutdown;
static void yurotsTermSignal(int)
{
	g_yurotsWantShutdown = 1;
}

int main(int argc, char *argv[])
{
	//Install crash handler FIRST — before any init that could segfault.
	//This is the only signal handler on Linux; the legacy EXCEPTION_TRACER
	//below is Windows-only (SEH) and does nothing on i386 Linux.
	CrashHandler::install();

	std::cout << ":: YurOTS 0.9.4f" << std::endl;
	std::cout << ":: ~~~~~~~~~~~~~" << std::endl;

	std::cout << "::" << std::endl;

#ifdef _NO_ROOT_PERMISSION_
	if( getuid() == 0 || geteuid() == 0 )
	{
		std::cout << std::endl << "OTServ executed as root user, please login with a normal user." << std::endl;
		return 1;
	}
#endif

	// ignore sigpipe...
	struct sigaction sigh;
	sigh.sa_handler = SIG_IGN;
	sigemptyset(&sigh.sa_mask);
	sigh.sa_flags = 0;
	sigaction(SIGPIPE, &sigh, NULL);

	// Graceful stop for docker stop / deploy: flush players (daily tasks, inventory).
	struct sigaction sighTerm;
	sighTerm.sa_handler = yurotsTermSignal;
	sigemptyset(&sighTerm.sa_mask);
	sighTerm.sa_flags = 0;
	sigaction(SIGTERM, &sighTerm, NULL);
	sigaction(SIGINT, &sighTerm, NULL);

	// random numbers generator
	std::cout << ":: Initializing random numbers...   ";
	srand ( (unsigned int)time(NULL) );
	std::cout << "[done]" << std::endl;

	// read global config
	std::cout << ":: Loading lua script config.lua... ";
#ifdef _HOMEDIR_CONF_
	std::string configpath;
	configpath = getenv("HOME");
	configpath += "/.otserv/config.lua";
	if (!g_config.OpenFile(configpath.c_str()))
#else
	if (!g_config.OpenFile("config.lua"))
#endif
	{
		ErrorMessage("Unable to load config.lua!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	IOPlayer::normalizePlayerFilenames(g_config.getGlobalString("datadir"));

	//load spells data
	std::cout << ":: Loading spells.xml...            ";
	if(!spells.loadFromXml(g_config.getGlobalString("datadir")))
	{
		ErrorMessage("Unable to load spells.xml!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	//load actions data
	std::cout << ":: Loading actions.xml...           ";
	if(!actions.loadFromXml(g_config.getGlobalString("datadir")))
	{
		ErrorMessage("Unable to load actions.xml!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	//load commands data
	std::cout << ":: Loading commands.xml...          ";
	if(!commands.loadXml(g_config.getGlobalString("datadir")))
	{
		ErrorMessage("Unable to load commands.xml!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	// load item data
	std::string itemsOtbPath = g_config.getGlobalString("items_otb", g_config.getGlobalString("datadir") + "items/items.otb");
	std::string itemsXmlPath = g_config.getGlobalString("items_xml", g_config.getGlobalString("datadir") + "items/items.xml");
	if(const char* envItemsOtb = getenv("YUROTS_ITEMS_OTB"))
	{
		if(*envItemsOtb)
			itemsOtbPath = envItemsOtb;
	}
	if(const char* envItemsXml = getenv("YUROTS_ITEMS_XML"))
	{
		if(*envItemsXml)
			itemsXmlPath = envItemsXml;
	}

	std::cout << ":: Loading items.otb...             ";
	if (Item::items.loadFromOtb(itemsOtbPath))
	{
		ErrorMessage("Could not load items.otb!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	std::cout << ":: Loading items.xml...             ";
	if (!Item::items.loadXMLInfos(itemsXmlPath))
	{
		ErrorMessage("Could not load /items/items.xml ...!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	std::cout << ":: Loading guilds.xml...            ";
	if (!Guilds::Load())
	{
		ErrorMessage("Could not load guilds.xml!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	std::cout << ":: Loading queue.xml...             ";
	if (!g_game.loginQueue.load())
	{
		ErrorMessage("Could not load queue.xml!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	std::cout << ":: Loading summons.xml...           ";
	if (!Summons::Load())
	{
		ErrorMessage("Could not load summons.xml!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	// load monster data
	std::cout << ":: Loading monsters.xml...          ";
	if(!g_monsters.loadFromXml(g_config.getGlobalString("datadir")))
	{
		ErrorMessage("Could not load monsters/monsters.xml!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	std::string worldtype = g_config.getGlobalString("worldtype");
	std::transform(worldtype.begin(), worldtype.end(), worldtype.begin(), upchar);
	if(worldtype == "PVP")
		g_game.setWorldType(WORLD_TYPE_PVP);
	else if(worldtype == "NO-PVP")
		g_game.setWorldType(WORLD_TYPE_NO_PVP);
	else if(worldtype == "PVP-ENFORCED")
		g_game.setWorldType(WORLD_TYPE_PVP_ENFORCED);
	else{
		ErrorMessage("Unknown world type!");
		return -1;
	}
	std::cout << ":: World Type: " << worldtype << std::endl;

	if(g_config.getGlobalString("md5passwords") == "yes"){
		passwordType = PASSWORD_TYPE_MD5;
		std::cout << ":: Use MD5 passwords" << std::endl;
	}
	else{
		passwordType = PASSWORD_TYPE_PLAIN;
	}

	timer();

	// loads the map and, if needed, an extra-file spawns
	switch(g_game.loadMap(g_config.getGlobalString("map"), g_config.getGlobalString("mapkind"))){
	case SPAWN_BUILTIN:
		break;
	case MAP_LOADER_ERROR:
		std::cout << "FATAL: couldnt determine the map format! exiting2" << std::endl;
		exit(1);
		break;
	case SPAWN_XML:
		SpawnManager::initialize(&g_game);
		SpawnManager::instance()->loadSpawnsXML(g_game.getSpawnFile());
		SpawnManager::instance()->startup();
		break;
	}

	double t = timer();
	std::cout << "Loaded in " << t << " s" << std::endl;

	std::cout << ":: Loading npc.xml...               ";
	if (!g_game.loadNpcs())
	{
		ErrorMessage("Could not load npc.xml!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	std::cout << ":: Loading houses.xml...            ";
	if (!Houses::Load(&g_game))
	{
		ErrorMessage("Could not load houses!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	std::cout << ":: Loading private_trainers.xml...  ";
	if (!PrivateTrainers::Load(&g_game))
	{
		ErrorMessage("Could not load private_trainers.xml!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	std::cout << ":: Loading pvparenas.xml...         ";
	if (!PvpArena::Load(&g_game))
	{
		ErrorMessage("Could not load pvparenas.xml!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	std::cout << ":: Loading trainingareas.xml...    ";
	if (!TrainingArea::Load(&g_game))
	{
		ErrorMessage("Could not load trainingareas.xml!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	std::cout << ":: Loading readables.xml...         ";
	if (!Readables::Load(&g_game))
	{
		ErrorMessage("Could not load readables.xml!");
		return -1;
	}
	std::cout << "[done]" << std::endl;

	if (g_config.getGlobalNumber("autosave") > 0)
		g_game.addEvent(makeTask(g_config.getGlobalNumber("autosave")*60000, std::mem_fun(&Game::autoServerSave)));
	else
		std::cout << ":: Auto server save disabled!" << std::endl;
	// Always poll save/shutdown requests (deploy + docker stop).
	g_game.addEvent(makeTask(2000, std::mem_fun(&Game::checkSaveRequest)));

  	// Call to WSA Startup on Windows Systems...

	std::string localip = "127.0.0.1";

	std::pair<unsigned long, unsigned long> IpNetMask;
	IpNetMask.first  = inet_addr("127.0.0.1");
	IpNetMask.second = 0xFFFFFFFF;
	serverIPs.push_back(IpNetMask);

	char szHostName[128];
	if (gethostname(szHostName, 128) == 0)
	{
		std::cout << "::" << std::endl << ":: Running on host " << szHostName << std::endl;

		hostent *he = gethostbyname(szHostName);

		if (he)
		{
			std::cout << ":: Local IP address(es):  ";
			unsigned char** addr = (unsigned char**)he->h_addr_list;

			if (addr[0])
			{
				localip = str(int(addr[0][0])) + "." + str(int(addr[0][1])) + 
					"." + str(int(addr[0][2])) + "." + str(int(addr[0][3]));
			}

			while (addr[0] != NULL)
			{
				std::cout << (unsigned int)(addr[0][0]) << "."
				<< (unsigned int)(addr[0][1]) << "."
				<< (unsigned int)(addr[0][2]) << "."
				<< (unsigned int)(addr[0][3]) << "  ";

			IpNetMask.first  = *(unsigned long*)(*addr);
			IpNetMask.second = 0x0000FFFF;
			serverIPs.push_back(IpNetMask);

			addr++;
			}

		std::cout << std::endl;
    		}
  	}

	std::cout << ":: Global IP address:     ";
	std::string ip;

	if(argc > 1)
		ip = argv[1];
	else
		ip = g_config.getGlobalString("ip", "127.0.0.1");

	if (ip == "auto")
		ip = localip;

	std::cout << ip << std::endl << "::" << std::endl;

	if (ip == "127.0.0.1")
		std::cout << "WARNING: Change your IP in config.lua!\n" << std::endl;

	IpNetMask.first  = resolveHostToIPv4(ip);
	IpNetMask.second = 0;
	serverIPs.push_back(IpNetMask);
	std::cout << ":: Starting Server... ";

	Status* status = Status::instance();
	status->playersmax = g_config.getGlobalNumber("maxplayers");

	// start the server listen...
	int listen_errors;
	int accept_errors;
	listen_errors = 0;
	while(g_game.getGameState() != GAME_STATE_SHUTDOWN && listen_errors < 100){
		sockaddr_in local_adress;
		memset(&local_adress, 0, sizeof(sockaddr_in)); // zero the struct

		local_adress.sin_family      = AF_INET;
		local_adress.sin_port        = htons(atoi(g_config.getGlobalString("port").c_str()));
		local_adress.sin_addr.s_addr = htonl(INADDR_ANY);

		// first we create a new socket
		SOCKET listen_socket = socket(AF_INET, SOCK_STREAM, 0);

		if(listen_socket <= 0){
			ErrorMessage("Unable to create server socket (1)!");
			return -1;
  		}

		int yes = 1;
		// lose the pesky "Address already in use" error message
		if(setsockopt(listen_socket, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof (int)) == -1){
			ErrorMessage("Unable to set socket options!");
			return -1;
		}

		// bind socket on port
		if(bind(listen_socket, (struct sockaddr*)&local_adress, sizeof(struct sockaddr_in)) < 0){
			ErrorMessage("Unable to create server socket (2)!");
			return -1;
  		}

		// now we start listen on the new socket
		if(listen(listen_socket, 128) == SOCKET_ERROR){
    			ErrorMessage("Listen on server socket not possible!");
			return -1;
		}

		std::cout << "[done]" << std::endl << ":: " << g_config.getGlobalString("servername") << " Server Running..." << std::endl;
		accept_errors = 0;
		while(g_game.getGameState() != GAME_STATE_SHUTDOWN && accept_errors < 100){
			fd_set listen_set;
			timeval tv;
			FD_ZERO(&listen_set);
			FD_SET(listen_socket, &listen_set);
			tv.tv_sec = 1;
			tv.tv_usec = 0;

			int reads = select((int)listen_socket + 1, &listen_set, NULL, NULL, &tv);
			int errnum;
			errnum = errno;
			if(reads == SOCKET_ERROR){
				if(errnum == ERROR_EINTR)
					continue;
				std::cout << ":: Listen select failed (errno=" << errnum << "), reopening port..." << std::endl;
				break;
			}
			if(reads == 0)
				continue;

			SOCKET s = accept(listen_socket, NULL, NULL);
			if(s > 0){
				SOCKET* sock = new SOCKET(s);
				OTSYS_CREATE_THREAD(ConnectionHandler, (void*)sock);
			}
			else{
					accept_errors++;
			}
		}
		closesocket(listen_socket);
		listen_errors++;
  	}

	return 0;
}
