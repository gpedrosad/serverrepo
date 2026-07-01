#ifndef __SOCKET_DEBUG_H__
#define __SOCKET_DEBUG_H__

#include "definitions.h"
#include "otsystem.h"
#include <string>

// Logs de red para diagnosticar kicks y cuelgues en 7171.
//
// Desconexiones: siempre imprimen una línea con sock/errno/timeout (grep "Player recv disconnect").
// Verbose: export YUROTS_SOCKET_DEBUG=1 antes de arrancar el OT (login, socket opts, reintentos recv).
//
// En Docker/VPS (cuando se despliegue):
//   docker logs -f yurots 2>&1 | grep -E '\[socket\]|Player recv disconnect'

bool socketDebugVerbose();
void socketDebugLog(const std::string& message);
int socketGetRecvTimeoutMs(SOCKET sock);
bool socketIsNonBlocking(SOCKET sock);
std::string socketDescribeState(SOCKET sock);
std::string socketPeerIp(SOCKET sock);
void socketLogDisconnect(const char* playerName, SOCKET sock, const char* reason, int errnum);

#endif
