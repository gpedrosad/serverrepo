//////////////////////////////////////////////////////////////////////
// CrashHandler — POSIX signal handler with backtrace + player snapshot
//////////////////////////////////////////////////////////////////////

#include "crashhandler.h"

#include <signal.h>
#include <execinfo.h>
#include <ucontext.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>
#include <sys/types.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

//Player + AutoList access for the snapshot. We include these so the
//handler can iterate Player::listPlayer and read each Player's getters.
#include "player.h"

// ---------------------------------------------------------------------------
// Signal name table
// ---------------------------------------------------------------------------
static const char* signal_name(int sig)
{
	switch (sig) {
		case SIGSEGV: return "SIGSEGV";
		case SIGABRT: return "SIGABRT";
		case SIGFPE:  return "SIGFPE";
		case SIGILL:  return "SIGILL";
		case SIGBUS:  return "SIGBUS";
		default:      return "UNKNOWN";
	}
}

// ---------------------------------------------------------------------------
// Minimal async-signal-safe writer
// ---------------------------------------------------------------------------
static void safe_write(int fd, const char* s, size_t n)
{
	if (fd < 0 || !s) return;
	while (n > 0) {
		ssize_t w = write(fd, s, n);
		if (w <= 0) return;
		s += w;
		n -= (size_t)w;
	}
}

static void safe_str(int fd, const char* s)
{
	if (s) safe_write(fd, s, strlen(s));
}

static void safe_line(int fd, const char* s)
{
	safe_str(fd, s);
	safe_str(fd, "\n");
}

//Hex-encode a 32-bit value into a fixed-width field.
static void safe_hex32(int fd, const char* label, uint32_t v)
{
	char buf[64];
	int n = snprintf(buf, sizeof(buf), "%s 0x%08x\n", label, v);
	if (n > 0) safe_write(fd, buf, (size_t)n);
}

// ---------------------------------------------------------------------------
// Filename helpers — use UTC to avoid TZ issues between Mac dev and VPS
// ---------------------------------------------------------------------------
static void make_crash_filename(char* out, size_t outsize)
{
	time_t now = time(NULL);
	struct tm tm;
	gmtime_r(&now, &tm);
	//data/crash-YYYYMMDD-HHMMSS.log
	strftime(out, outsize, "data/crash-%Y%m%d-%H%M%S.log", &tm);
}

static void make_snapshot_filename(char* out, size_t outsize, const char* stamp)
{
	//data/snapshot-YYYYMMDD-HHMMSS.txt
	snprintf(out, outsize, "data/snapshot-%s.txt", stamp);
}

// ---------------------------------------------------------------------------
// Player snapshot — written to a SEPARATE file so the crash log stays clean
// ---------------------------------------------------------------------------
static void dump_players_snapshot(const char* crash_filename)
{
	//Derive the timestamp string from the crash filename.
	//crash_filename looks like: data/crash-20260630-123045.log
	const char* stamp = strstr(crash_filename, "crash-");
	if (!stamp) return;
	stamp += strlen("crash-");

	char snapname[128];
	make_snapshot_filename(snapname, sizeof(snapname), stamp);

	int fd = open(snapname, O_WRONLY | O_CREAT | O_TRUNC, 0644);
	if (fd < 0) {
		//fall back to stdout
		fd = STDOUT_FILENO;
	}

	safe_line(fd, "============================================");
	safe_line(fd, "YurOTS PLAYER SNAPSHOT (taken at crash time)");
	safe_line(fd, "============================================");

	char hdr[128];
	time_t now = time(NULL);
	struct tm tm;
	gmtime_r(&now, &tm);
	strftime(hdr, sizeof(hdr), "Snapshot UTC: %Y-%m-%d %H:%M:%S\n", &tm);
	safe_str(fd, hdr);

	int n = snprintf(hdr, sizeof(hdr), "Crash file:   %s\n", crash_filename);
	if (n > 0) safe_write(fd, hdr, (size_t)n);
	safe_line(fd, "");

	//Iterate Player::listPlayer.list (std::map<unsigned long, Player*>)
	int online = 0;
	for (AutoList<Player>::listiterator it = Player::listPlayer.list.begin();
		 it != Player::listPlayer.list.end(); ++it) {

		Player* p = it->second;
		if (!p) continue;

		const char* name = p->getName().c_str();
		int level  = p->getLevel();
		int health = (int)p->getHealth();
		int hp_max = (int)p->healthmax;
		int64_t mana = p->getMana();
		int64_t mn_max = p->manamax;
		int voc = (int)p->getVocation();
		int x = p->pos.x;
		int y = p->pos.y;
		int z = p->pos.z;

		//voc id is stable; we just print the int — readable + JSON-friendly.
		char line[512];
		int len = snprintf(line, sizeof(line),
			"  player id=%lu name=\"%s\" lvl=%d voc=%d "
			"hp=%d/%d mp=%lld/%lld pos=(%d,%d,%d)\n",
			it->first, name, level, voc,
			health, hp_max, (long long)mana, (long long)mn_max,
			x, y, z);
		if (len > 0) safe_write(fd, line, (size_t)len);
		online++;
	}

	int len = snprintf(hdr, sizeof(hdr), "\nTotal online: %d\n", online);
	if (len > 0) safe_write(fd, hdr, (size_t)len);

	if (fd != STDOUT_FILENO) close(fd);
}

// ---------------------------------------------------------------------------
// Main signal handler
// ---------------------------------------------------------------------------
static void crash_signal_handler(int sig, siginfo_t* info, void* ucontext)
{
	//Restore default handler first so if the write itself segfaults we still die.
	signal(sig, SIG_DFL);

	char crash_filename[128];
	make_crash_filename(crash_filename, sizeof(crash_filename));

	//Also try to dump a copy to stdout (so it lands in `docker logs`).
	int fd = open(crash_filename, O_WRONLY | O_CREAT | O_TRUNC, 0644);
	bool to_file = (fd >= 0);

	//Header
	safe_line(fd, "============================================");
	safe_line(fd, "YurOTS CRASH REPORT");
	safe_line(fd, "============================================");

	//Signal info
	char buf[256];
	int n = snprintf(buf, sizeof(buf), "Signal:    %d (%s)\n", sig, signal_name(sig));
	if (n > 0) safe_write(fd, buf, (size_t)n);

	time_t now = time(NULL);
	struct tm tm;
	gmtime_r(&now, &tm);
	strftime(buf, sizeof(buf), "Time UTC:  %Y-%m-%d %H:%M:%S\n", &tm);
	safe_str(fd, buf);

	n = snprintf(buf, sizeof(buf), "PID:       %d\n", (int)getpid());
	if (n > 0) safe_write(fd, buf, (size_t)n);

	n = snprintf(buf, sizeof(buf), "UID/EUID:  %d / %d\n", (int)getuid(), (int)geteuid());
	if (n > 0) safe_write(fd, buf, (size_t)n);

	if (info) {
		n = snprintf(buf, sizeof(buf), "Fault addr: %p\n", info->si_addr);
		if (n > 0) safe_write(fd, buf, (size_t)n);
		n = snprintf(buf, sizeof(buf), "si_code:    %d\n", info->si_code);
		if (n > 0) safe_write(fd, buf, (size_t)n);
	}

	//Backtrace
	void* bt[64];
	int bt_count = backtrace(bt, 64);

	//Write backtrace to the file using backtrace_symbols_fd (async-signal-safe).
	//This writes raw symbol strings without malloc'ing the array.
	if (to_file) {
		backtrace_symbols_fd(bt, bt_count, fd);
	} else {
		//fallback: print to stdout
		backtrace_symbols_fd(bt, bt_count, STDOUT_FILENO);
	}

	//Registers from ucontext (i386)
	if (ucontext) {
		ucontext_t* ctx = (ucontext_t*)ucontext;
		safe_line(fd, "");
		safe_line(fd, "--- Registers (i386) ---");
		safe_hex32(fd, "EAX:", (uint32_t)ctx->uc_mcontext.gregs[REG_EAX]);
		safe_hex32(fd, "EBX:", (uint32_t)ctx->uc_mcontext.gregs[REG_EBX]);
		safe_hex32(fd, "ECX:", (uint32_t)ctx->uc_mcontext.gregs[REG_ECX]);
		safe_hex32(fd, "EDX:", (uint32_t)ctx->uc_mcontext.gregs[REG_EDX]);
		safe_hex32(fd, "ESI:", (uint32_t)ctx->uc_mcontext.gregs[REG_ESI]);
		safe_hex32(fd, "EDI:", (uint32_t)ctx->uc_mcontext.gregs[REG_EDI]);
		safe_hex32(fd, "EBP:", (uint32_t)ctx->uc_mcontext.gregs[REG_EBP]);
		safe_hex32(fd, "ESP:", (uint32_t)ctx->uc_mcontext.gregs[REG_ESP]);
		safe_hex32(fd, "EIP:", (uint32_t)ctx->uc_mcontext.gregs[REG_EIP]);
	}

	safe_line(fd, "");
	n = snprintf(buf, sizeof(buf), "Saved crash report to: %s\n", crash_filename);
	if (n > 0) safe_write(fd, buf, (size_t)n);

	//Dump the player snapshot to a separate file.
	//We do this from the same handler so it always pairs with the crash.
	dump_players_snapshot(crash_filename);

	if (to_file) close(fd);

	//Also print a one-liner to stdout so the death is visible in `docker logs`.
	n = snprintf(buf, sizeof(buf),
		":: [crash] signal=%s saved=%s pid=%d\n",
		signal_name(sig), crash_filename, (int)getpid());
	if (n > 0) write(STDOUT_FILENO, buf, (size_t)n);

	//Flush stdio buffers if any.
	//(Not all libc's do this safely from a signal handler; best-effort.)
	fsync(STDOUT_FILENO);
	fsync(STDERR_FILENO);

	//Re-raise with default handler so the process dies (and dumps core if enabled).
	raise(sig);
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------
void CrashHandler::install()
{
	struct sigaction sa;
	memset(&sa, 0, sizeof(sa));
	sa.sa_sigaction = crash_signal_handler;
	sa.sa_flags = SA_SIGINFO | SA_RESETHAND;
	sigemptyset(&sa.sa_mask);

	sigaction(SIGSEGV, &sa, NULL);
	sigaction(SIGABRT, &sa, NULL);
	sigaction(SIGFPE,  &sa, NULL);
	sigaction(SIGILL,  &sa, NULL);
	sigaction(SIGBUS,  &sa, NULL);

	//SIGPIPE happens when a client disconnects during write — keep default (ignore).
	//We don't want to log every dropped connection as a "crash".
}

void CrashHandler::uninstall()
{
	struct sigaction sa;
	memset(&sa, 0, sizeof(sa));
	sa.sa_handler = SIG_DFL;
	sigemptyset(&sa.sa_mask);

	sigaction(SIGSEGV, &sa, NULL);
	sigaction(SIGABRT, &sa, NULL);
	sigaction(SIGFPE,  &sa, NULL);
	sigaction(SIGILL,  &sa, NULL);
	sigaction(SIGBUS,  &sa, NULL);
}

void CrashHandler::triggerTestCrash()
{
	//Force a SIGSEGV to validate the pipeline end-to-end.
	//Useful from a debug console or a /test_crash GM command.
	volatile int* p = NULL;
	*p = 0;
}
