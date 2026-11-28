#ifndef __PLAYLOG_H__
#define __PLAYLOG_H__

#include <string>

class Player;
class Creature;

// Registro de juego para medir los primeros pasos y la retención (docs/systems/PRIMEROS_PASOS.md).
// Una línea JSON por evento en data/logs/play-AAAA-MM.jsonl (junto a logins-*.jsonl). Las cuentas con
// access > 0 (GM) no se registran. Si no se puede escribir, el juego sigue igual.
//
// Eventos: "session" (resumen al salir), "pos" (posición cada 2 min hasta nivel 40), "level", "death".
// Los monstruos matados, el chat, el training y las zonas se suman en memoria y salen en "session".

// Abre la sesión de juego (login o reenganche). Devuelve el id de la sesión, que se pasa a playlogLogout
// para no cerrar por error una sesión nueva del mismo personaje (reemplazo de sesión).
long playlogLogin(Player* player, unsigned long account);
// Cierra la sesión: escribe "session" con lo que juntó. `reason`: logout, relogin.
void playlogLogout(const std::string& name, long sessionId, long durationSec);

// Cada pensamiento del jugador (Game::checkCreature, ~1 s).
void playlogTick(Player* player, int thinkTicks, bool inTraining, bool inPz);
// Monstruo muerto con exp para este jugador (también cada miembro de la party que recibe exp).
void playlogKill(Player* player, const std::string& monster, long long exp);
// Muerte del jugador, antes de aplicar la pérdida. `keptAll` = protección de novato.
void playlogDeath(Player* player, Creature* killer, long long lostExp, bool keptAll);
// Subió de nivel (de `fromLevel` a player->level).
void playlogLevel(Player* player, int fromLevel);
// Habló: 0 = decir en pantalla (incluye hablar con NPC), 1 = privado, 2 = canal.
void playlogChat(Player* player, int kind);

#endif
