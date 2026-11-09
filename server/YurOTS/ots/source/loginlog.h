#ifndef __LOGINLOG_H__
#define __LOGINLOG_H__

#include <string>

// Registro de accesos: una línea JSON por evento en data/logs/logins-AAAA-MM.jsonl
// (relativo al directorio de trabajo del servidor, /app/YurOTS/ots en Docker).
// Ver docs/systems/LOGIN_EVENTS.md. Nunca se registra la contraseña.
//
// event:  charlist_ok, charlist_fail, game_login, game_fail, game_reattach,
//         game_replace, game_logout
// reason: motivo del fallo (vacío si no aplica)
// value:  dato numérico opcional (versión del cliente, puesto en la cola,
//         duración de la sesión en segundos); -1 = no aplica
void loginLog(const std::string& event, unsigned long account, const std::string& name,
              const std::string& ip, const std::string& reason = "", long value = -1);

#endif
