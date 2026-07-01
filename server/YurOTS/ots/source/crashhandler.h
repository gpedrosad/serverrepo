//////////////////////////////////////////////////////////////////////
// CrashHandler — POSIX signal handler with backtrace + player snapshot
//
// Captures SIGSEGV / SIGABRT / SIGFPE / SIGILL / SIGBUS and writes:
//   - data/crash-<UTC-timestamp>.log   (stack, registers, signal info)
//   - data/snapshot-<UTC-timestamp>.txt (online players + their state)
//
// Designed for Linux/i386 (matches the project's Docker build target).
// Async-signal-safe: uses write() and backtrace_symbols_fd() only —
// no malloc / printf / iostreams from inside the handler.
//////////////////////////////////////////////////////////////////////

#ifndef __CRASH_HANDLER_H__
#define __CRASH_HANDLER_H__

namespace CrashHandler
{
	//Install handlers for SIGSEGV, SIGABRT, SIGFPE, SIGILL, SIGBUS.
	//Idempotent. Safe to call multiple times.
	void install();

	//Remove the handlers (restore default behavior).
	void uninstall();

	//Manual trigger for testing: dumps a crash report and aborts.
	//Useful to verify the pipeline from the GM console or a /test command.
	void triggerTestCrash();
}

#endif //__CRASH_HANDLER_H__
