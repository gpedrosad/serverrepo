#include "playlog.h"

#include "const76.h"
#include "game.h"
#include "luascript.h"
#include "player.h"

#include <cstdio>
#include <ctime>
#include <map>
#include <mutex>
#include <set>
#include <sstream>

#include <sys/stat.h>
#include <sys/types.h>

// Ver playlog.h y docs/systems/PRIMEROS_PASOS.md.

namespace {

const char* PLAY_LOG_DIR = "data/logs";
const int POS_EVERY_MS = 120000;     // una posición cada 2 minutos de juego
const int POS_MAX_LEVEL = 40;        // solo los primeros niveles (lo que interesa para retención)
const int DIED_LAST_SEC = 180;       // "se fue después de morir": murió en los últimos 3 min de la sesión

struct Session {
	long id;
	unsigned long acc;
	int voc;
	bool premium;
	time_t start;
	int lvl0, lvl;
	long long exp0, exp;
	int kills;
	std::map<std::string, int> monsters;
	int deaths, pvpDeaths;
	time_t lastDeath;
	std::string lastKiller;
	std::set<long long> zones;       // casillas de 32x32 por piso visitadas
	long trainMs, pzMs, partyMs, posMs, onlineMs;
	int says, privates, channel;
	int x, y, z, hpPct;
};

std::mutex playLogMutex;
std::map<std::string, Session> sessions;   // por nombre de personaje
long nextSessionId = 1;

std::string jsonEscape(const std::string& in)
{
	std::string out;
	out.reserve(in.size() + 2);
	for(std::string::size_type i = 0; i < in.size(); ++i){
		const unsigned char c = (unsigned char)in[i];
		switch(c){
			case '"':  out += "\\\""; break;
			case '\\': out += "\\\\"; break;
			case '\n': out += "\\n"; break;
			case '\r': out += "\\r"; break;
			case '\t': out += "\\t"; break;
			default:
				if(c < 0x20){
					char buf[8];
					std::snprintf(buf, sizeof(buf), "\\u%04x", c);
					out += buf;
				}
				else
					out += (char)c;
		}
	}
	return out;
}

// Comienzo de la línea: {"t":...,"ts":"...","event":"...","name":"..."
std::string lineStart(const char* event, const std::string& name, time_t now)
{
	struct tm utc;
	gmtime_r(&now, &utc);
	char stamp[32];
	std::strftime(stamp, sizeof(stamp), "%Y-%m-%dT%H:%M:%SZ", &utc);
	std::ostringstream line;
	line << "{\"t\":" << (long)now << ",\"ts\":\"" << stamp << "\",\"event\":\"" << event
	     << "\",\"name\":\"" << jsonEscape(name) << "\"";
	return line.str();
}

// Escribe una línea completa (ya cerrada con "}"). Llamar con playLogMutex tomado.
void writeLine(const std::string& text, time_t now)
{
	struct tm utc;
	gmtime_r(&now, &utc);
	char month[16];
	std::strftime(month, sizeof(month), "%Y-%m", &utc);
	const std::string path = std::string(PLAY_LOG_DIR) + "/play-" + month + ".jsonl";
	mkdir(PLAY_LOG_DIR, 0755);
	FILE* f = std::fopen(path.c_str(), "a");
	if(!f)
		return;
	const std::string line = text + "\n";
	std::fwrite(line.data(), 1, line.size(), f);
	std::fclose(f);
}

bool tracked(const Player* player)
{
	return player && player->access == 0;
}

int hpPercent(const Player* player)
{
	if(player->healthmax <= 0)
		return 0;
	long long pct = (long long)player->health * 100 / player->healthmax;
	return (int)(pct < 0 ? 0 : (pct > 100 ? 100 : pct));
}

void fillFromPlayer(Session& s, Player* player)
{
	s.lvl = player->level;
	s.exp = (long long)player->getExperience();
	s.x = player->pos.x;
	s.y = player->pos.y;
	s.z = player->pos.z;
	s.hpPct = hpPercent(player);
}

// Escribe "session" y la borra del mapa. Llamar con playLogMutex tomado.
void flushSession(const std::string& name, const Session& s, const char* reason, long durationSec, time_t now)
{
	std::ostringstream line;
	line << lineStart("session", name, now)
	     << ",\"acc\":" << s.acc << ",\"voc\":" << s.voc << ",\"prem\":" << (s.premium ? 1 : 0)
	     << ",\"reason\":\"" << reason << "\""
	     << ",\"start\":" << (long)s.start << ",\"dur\":" << durationSec
	     << ",\"online_s\":" << s.onlineMs / 1000
	     << ",\"lvl0\":" << s.lvl0 << ",\"lvl1\":" << s.lvl
	     << ",\"exp0\":" << s.exp0 << ",\"exp1\":" << s.exp
	     << ",\"kills\":" << s.kills << ",\"deaths\":" << s.deaths << ",\"pvp_deaths\":" << s.pvpDeaths
	     << ",\"died_last\":" << ((s.lastDeath > 0 && now - s.lastDeath <= DIED_LAST_SEC) ? 1 : 0);
	if(!s.lastKiller.empty())
		line << ",\"last_killer\":\"" << jsonEscape(s.lastKiller) << "\"";
	line << ",\"zones\":" << s.zones.size()
	     << ",\"train_s\":" << s.trainMs / 1000 << ",\"pz_s\":" << s.pzMs / 1000 << ",\"party_s\":" << s.partyMs / 1000
	     << ",\"says\":" << s.says << ",\"pms\":" << s.privates << ",\"chan\":" << s.channel
	     << ",\"x\":" << s.x << ",\"y\":" << s.y << ",\"z\":" << s.z << ",\"hp\":" << s.hpPct
	     << ",\"mons\":{";
	bool first = true;
	for(std::map<std::string, int>::const_iterator it = s.monsters.begin(); it != s.monsters.end(); ++it){
		line << (first ? "" : ",") << "\"" << jsonEscape(it->first) << "\":" << it->second;
		first = false;
	}
	line << "}}";
	writeLine(line.str(), now);
}

} // namespace

long playlogLogin(Player* player, unsigned long account)
{
	if(!tracked(player))
		return 0;
	const time_t now = std::time(NULL);
	std::lock_guard<std::mutex> lock(playLogMutex);
	const std::string name = player->getName();
	std::map<std::string, Session>::iterator old = sessions.find(name);
	if(old != sessions.end()){
		// Quedó abierta (reenganche o reemplazo): se cierra con lo que tenía.
		flushSession(name, old->second, "relogin", (long)(now - old->second.start), now);
		sessions.erase(old);
	}
	Session s;
	s.id = nextSessionId++;
	s.acc = account;
	s.voc = (int)player->getVocation();
	s.premium = player->isPremium();
	s.start = now;
	s.lvl0 = player->level;
	s.exp0 = (long long)player->getExperience();
	s.kills = 0;
	s.deaths = 0;
	s.pvpDeaths = 0;
	s.lastDeath = 0;
	s.trainMs = s.pzMs = s.partyMs = s.posMs = s.onlineMs = 0;
	s.says = s.privates = s.channel = 0;
	fillFromPlayer(s, player);
	sessions[name] = s;
	return s.id;
}

void playlogLogout(const std::string& name, long sessionId, long durationSec)
{
	if(sessionId <= 0)
		return;
	const time_t now = std::time(NULL);
	std::lock_guard<std::mutex> lock(playLogMutex);
	std::map<std::string, Session>::iterator it = sessions.find(name);
	if(it == sessions.end() || it->second.id != sessionId)
		return;   // ya la cerró un login nuevo del mismo personaje
	flushSession(name, it->second, "logout", durationSec, now);
	sessions.erase(it);
}

void playlogTick(Player* player, int thinkTicks, bool inTraining, bool inPz)
{
	if(!tracked(player) || thinkTicks <= 0)
		return;
	const time_t now = std::time(NULL);
	std::lock_guard<std::mutex> lock(playLogMutex);
	std::map<std::string, Session>::iterator it = sessions.find(player->getName());
	if(it == sessions.end())
		return;
	Session& s = it->second;
	fillFromPlayer(s, player);
	s.onlineMs += thinkTicks;
	if(inTraining)
		s.trainMs += thinkTicks;
	if(inPz)
		s.pzMs += thinkTicks;
	if(player->party != 0)
		s.partyMs += thinkTicks;
	s.zones.insert(((long long)player->pos.z << 32) | ((long long)(player->pos.y >> 5) << 16) | (long long)(player->pos.x >> 5));

	s.posMs += thinkTicks;
	if(s.posMs >= POS_EVERY_MS){
		s.posMs = 0;
		if(player->level <= POS_MAX_LEVEL){
			std::ostringstream line;
			line << lineStart("pos", player->getName(), now)
			     << ",\"acc\":" << s.acc << ",\"lvl\":" << player->level
			     << ",\"x\":" << s.x << ",\"y\":" << s.y << ",\"z\":" << s.z << ",\"hp\":" << s.hpPct
			     << ",\"train\":" << (inTraining ? 1 : 0) << ",\"pz\":" << (inPz ? 1 : 0)
			     << ",\"party\":" << (player->party != 0 ? 1 : 0) << "}";
			writeLine(line.str(), now);
		}
	}
}

void playlogKill(Player* player, const std::string& monster, long long exp)
{
	if(!tracked(player))
		return;
	std::lock_guard<std::mutex> lock(playLogMutex);
	std::map<std::string, Session>::iterator it = sessions.find(player->getName());
	if(it == sessions.end())
		return;
	it->second.kills++;
	it->second.monsters[monster]++;
	(void)exp;
}

void playlogDeath(Player* player, Creature* killer, long long lostExp, bool keptAll)
{
	if(!tracked(player))
		return;
	const time_t now = std::time(NULL);
	std::string killerName = killer ? killer->getName() : "";
	Creature* master = killer ? killer->getMaster() : NULL;
	const bool byPlayer = (killer && dynamic_cast<Player*>(killer)) || (master && dynamic_cast<Player*>(master));
	std::lock_guard<std::mutex> lock(playLogMutex);
	std::map<std::string, Session>::iterator it = sessions.find(player->getName());
	unsigned long acc = 0;
	if(it != sessions.end()){
		Session& s = it->second;
		s.deaths++;
		if(byPlayer)
			s.pvpDeaths++;
		s.lastDeath = now;
		s.lastKiller = killerName;
		acc = s.acc;
	}
	std::ostringstream line;
	line << lineStart("death", player->getName(), now)
	     << ",\"acc\":" << acc << ",\"lvl\":" << player->level
	     << ",\"killer\":\"" << jsonEscape(killerName) << "\",\"pvp\":" << (byPlayer ? 1 : 0)
	     << ",\"lost_exp\":" << lostExp << ",\"kept\":" << (keptAll ? 1 : 0)
	     << ",\"x\":" << player->pos.x << ",\"y\":" << player->pos.y << ",\"z\":" << player->pos.z << "}";
	writeLine(line.str(), now);
}

void playlogLevel(Player* player, int fromLevel)
{
	if(!tracked(player))
		return;
	const time_t now = std::time(NULL);
	std::lock_guard<std::mutex> lock(playLogMutex);
	std::map<std::string, Session>::iterator it = sessions.find(player->getName());
	unsigned long acc = 0;
	long sessionSec = 0;
	if(it != sessions.end()){
		it->second.lvl = player->level;
		acc = it->second.acc;
		sessionSec = (long)(now - it->second.start);
	}
	std::ostringstream line;
	line << lineStart("level", player->getName(), now)
	     << ",\"acc\":" << acc << ",\"from\":" << fromLevel << ",\"to\":" << player->level
	     << ",\"session_s\":" << sessionSec
	     << ",\"x\":" << player->pos.x << ",\"y\":" << player->pos.y << ",\"z\":" << player->pos.z << "}";
	writeLine(line.str(), now);
}

void playlogChat(Player* player, int kind)
{
	if(!tracked(player))
		return;
	std::lock_guard<std::mutex> lock(playLogMutex);
	std::map<std::string, Session>::iterator it = sessions.find(player->getName());
	if(it == sessions.end())
		return;
	if(kind == 1)
		it->second.privates++;
	else if(kind == 2)
		it->second.channel++;
	else
		it->second.says++;
}
