#include "socket_debug.h"

#include <cstdlib>
#include <iostream>
#include <sstream>

#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <arpa/inet.h>

bool socketDebugVerbose()
{
	static int cached = -1;
	if(cached < 0){
		const char* v = std::getenv("YUROTS_SOCKET_DEBUG");
		cached = (v && (v[0] == '1' || v[0] == 'y' || v[0] == 'Y')) ? 1 : 0;
	}
	return cached == 1;
}

void socketDebugLog(const std::string& message)
{
	if(!socketDebugVerbose())
		return;
	std::cout << "[socket] " << message << std::endl;
}

int socketGetRecvTimeoutMs(SOCKET sock)
{
	if(sock <= 0)
		return -1;
	struct timeval tv;
	socklen_t len = sizeof(tv);
	if(getsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, &len) != 0)
		return -1;
	return (int)(tv.tv_sec * 1000 + tv.tv_usec / 1000);
}

bool socketIsNonBlocking(SOCKET sock)
{
	if(sock <= 0)
		return false;
	int flags = fcntl(sock, F_GETFL, 0);
	if(flags == -1)
		return false;
	return (flags & O_NONBLOCK) != 0;
}

std::string socketDescribeState(SOCKET sock)
{
	std::ostringstream os;
	os << "sock=" << sock;
	os << " rcv_ms=" << socketGetRecvTimeoutMs(sock);
	os << " nonblock=" << (socketIsNonBlocking(sock) ? 1 : 0);
	return os.str();
}

std::string socketPeerIp(SOCKET sock)
{
	if(sock <= 0)
		return "?";
	sockaddr_in peer;
	socklen_t len = sizeof(peer);
	if(getpeername(sock, (sockaddr*)&peer, &len) != 0)
		return "?";
	char buf[INET_ADDRSTRLEN];
	if(inet_ntop(AF_INET, &peer.sin_addr, buf, sizeof(buf)))
		return buf;
	return "?";
}

void socketLogDisconnect(const char* playerName, SOCKET sock, const char* reason, int errnum)
{
	std::ostringstream os;
	os << "Player recv disconnect: ";
	if(playerName && playerName[0])
		os << playerName;
	else
		os << "?";
	os << " (" << (reason && reason[0] ? reason : "unknown") << ")";
	os << " " << socketDescribeState(sock);
	if(errnum != 0){
		os << " errno=" << errnum;
		os << " (" << std::strerror(errnum) << ")";
	}
	std::cout << os.str() << std::endl;
}
