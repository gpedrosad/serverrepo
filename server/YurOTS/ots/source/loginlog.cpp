#include "loginlog.h"

#include <cstdio>
#include <ctime>
#include <mutex>
#include <sstream>

#include <sys/stat.h>
#include <sys/types.h>

namespace {

std::mutex loginLogMutex;
const char* LOGIN_LOG_DIR = "data/logs";

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

} // namespace

void loginLog(const std::string& event, unsigned long account, const std::string& name,
              const std::string& ip, const std::string& reason, long value)
{
	const time_t now = std::time(NULL);
	struct tm utc;
	gmtime_r(&now, &utc);
	char stamp[32];
	std::strftime(stamp, sizeof(stamp), "%Y-%m-%dT%H:%M:%SZ", &utc);
	char month[16];
	std::strftime(month, sizeof(month), "%Y-%m", &utc);

	std::ostringstream line;
	line << "{\"t\":" << (long)now
	     << ",\"ts\":\"" << stamp << "\""
	     << ",\"event\":\"" << jsonEscape(event) << "\""
	     << ",\"acc\":" << account
	     << ",\"name\":\"" << jsonEscape(name) << "\""
	     << ",\"ip\":\"" << jsonEscape(ip) << "\"";
	if(!reason.empty())
		line << ",\"reason\":\"" << jsonEscape(reason) << "\"";
	if(value >= 0)
		line << ",\"value\":" << value;
	line << "}\n";

	const std::string path = std::string(LOGIN_LOG_DIR) + "/logins-" + month + ".jsonl";
	const std::string text = line.str();

	std::lock_guard<std::mutex> lock(loginLogMutex);
	mkdir(LOGIN_LOG_DIR, 0755); // ya existe casi siempre; el error se ignora
	// Si no se puede escribir, el login sigue igual: el registro nunca bloquea el juego.
	FILE* f = std::fopen(path.c_str(), "a");
	if(!f)
		return;
	std::fwrite(text.data(), 1, text.size(), f);
	std::fclose(f);
}
