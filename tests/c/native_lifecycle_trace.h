/* TEST ONLY: copied LMDB native lifecycle trace; never included by production.
 * No native result injection, manual resource deletion or hidden retry.
 */
#ifndef DML_NATIVE_LIFECYCLE_TRACE_H
#define DML_NATIVE_LIFECYCLE_TRACE_H
#include <stdint.h>

void nlc_event(const char *, int, unsigned long, int, intptr_t, const char *);
void nlc_namespace(const char *, const char *, const char *);
void nlc_close_exclusive(int);
void nlc_shared_attempt_ready(void);
void nlc_windows_named_closed(void);

/* GetLastError must be captured FIRST, before even CRT errno/logging helpers. */
#ifdef _WIN32
#define NLC_SAVE DWORD nlc_saved_os = GetLastError(); int nlc_saved_errno = errno
#define NLC_RESTORE do { errno = nlc_saved_errno; SetLastError(nlc_saved_os); } while (0)
#else
#define NLC_SAVE int nlc_saved_errno = errno; unsigned long nlc_saved_os = (unsigned long)nlc_saved_errno
#define NLC_RESTORE do { errno = nlc_saved_errno; } while (0)
#endif
#define NLC_NOTE(event, result, exclusive, fd, name) do { \
  NLC_SAVE; \
  nlc_event(event, result, (unsigned long)nlc_saved_os, exclusive, (intptr_t)(fd), name); \
  NLC_RESTORE; \
} while (0)
#define NLC_NAMESPACE(stage, reader, writer) do { \
  NLC_SAVE; nlc_namespace(stage, reader, writer); NLC_RESTORE; \
} while (0)
#define NLC_CLOSE_EXCLUSIVE(exclusive) do { \
  NLC_SAVE; nlc_close_exclusive(exclusive); NLC_RESTORE; \
} while (0)
#define NLC_SHARED_ATTEMPT_READY() do { \
  NLC_SAVE; nlc_shared_attempt_ready(); NLC_RESTORE; \
} while (0)
#define NLC_WINDOWS_NAMED_CLOSED() do { \
  NLC_SAVE; nlc_windows_named_closed(); NLC_RESTORE; \
} while (0)
/* Original sem_unlink exactly ONCE, solely inside original lifecycle sites. */
#define NLC_ORIGINAL_UNLINK(event, name) do { \
  const char *nlc_name = name; \
  NLC_NOTE("unlink-enter", 0, -1, -1, nlc_name); \
  int nlc_unlink_result = sem_unlink(nlc_name); \
  NLC_NOTE(event, nlc_unlink_result, -1, -1, nlc_name); \
} while (0)
#endif
