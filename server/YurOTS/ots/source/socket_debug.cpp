#include "socket_debug.h"

#include <cstdlib>
#include <iostream>
#include <sstream>

#if !defined WIN32 && !defined __WINDOWS__
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <arpa/inet.h>
#endif

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
#if defined WIN32 || defined __WINDOWS__
	DWORD ms = 0;
	int len = (int)sizeof(ms);
	if(getsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (char*)&ms, &len) != 0)
		return -1;
	return (int)ms;
#else
	struct timeval tv;
	socklen_t len = sizeof(tv);
	if(getsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, &len) != 0)
		return -1;
	return (int)(tv.tv_sec * 1000 + tv.tv_usec / 1000);
#endif
}

bool socketIsNonBlocking(SOCKET sock)
{
	if(sock <= 0)
		return false;
#if defined WIN32 || defined __WINDOWS__
	unsigned long mode = 0;
	if(ioctlsocket(sock, FIONBIO, &mode) != 0)
		return false;
	return mode != 0;
#else
	int flags = fcntl(sock, F_GETFL, 0);
	if(flags == -1)
		return false;
	return (flags & O_NONBLOCK) != 0;
#endif
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
#if defined WIN32 || defined __WINDOWS__
	char buf[32];
	sprintf(buf, "%u", (unsigned)peer.sin_addr.S_un.S_addr);
	return buf;
#else
	char buf[INET_ADDRSTRLEN];
	if(inet_ntop(AF_INET, &peer.sin_addr, buf, sizeof(buf)))
		return buf;
	return "?";
#endif
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
#if !defined WIN32 && !defined __WINDOWS__
		os << " (" << std::strerror(errnum) << ")";
#endif
	}
	std::cout << os.str() << std::endl;
}
