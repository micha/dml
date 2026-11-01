/* TEST ONLY, standalone copied LMDB with ACTUAL platform backend.
 * Python starts BOTH actors before start marker: one environment per process,
 * no inherited environment, transactions, Q/T, manual unlink or extra retained
 * named-resource handles. Not a reproduction/diagnosis of historical CI.
 */
#define _XOPEN_SOURCE 700
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#include <direct.h>
#define BACKEND "windows-mutex"
#else
#include <unistd.h>
#ifdef __APPLE__
#include <semaphore.h>
#define BACKEND "mac-posix-sem"
#else
#define BACKEND "linux-posix-mutex"
#endif
#endif
#include "lmdb.h"
#include "native_lifecycle_trace.h"

static struct {
  char root[4096];
  char names[2][64];
  FILE *trace;
  unsigned count;
  int actor; /* 1 closer; 2 opener */
  int overlap, closing, failed_exclusive, aborted;
} state;

static unsigned long long monotonic_ns(void) {
#ifdef _WIN32
  LARGE_INTEGER value, frequency;
  if (!QueryPerformanceCounter(&value) || !QueryPerformanceFrequency(&frequency)) return 0;
  return (unsigned long long)(value.QuadPart / frequency.QuadPart) * 1000000000ULL +
    (unsigned long long)(value.QuadPart % frequency.QuadPart) * 1000000000ULL / (unsigned long long)frequency.QuadPart;
#else
  struct timespec ts;
  if (clock_gettime(CLOCK_MONOTONIC, &ts)) return 0;
  return (unsigned long long)ts.tv_sec * 1000000000ULL + (unsigned long long)ts.tv_nsec;
#endif
}
static long own_pid(void) {
#ifdef _WIN32
  return (long)GetCurrentProcessId();
#else
  return (long)getpid();
#endif
}
static void fatal(const char *reason);

void nlc_event(const char *event, int result, unsigned long native_error,
               int exclusive, intptr_t descriptor, const char *name) {
  NLC_SAVE;
  unsigned long long dev = 0, ino = 0;
  if (descriptor != (intptr_t)-1) {
#ifdef _WIN32
    BY_HANDLE_FILE_INFORMATION info;
    if (GetFileInformationByHandle((HANDLE)descriptor, &info)) {
      dev = info.dwVolumeSerialNumber;
      ino = ((unsigned long long)info.nFileIndexHigh << 32) | info.nFileIndexLow;
    }
#else
    struct stat info;
    if (fstat((int)descriptor, &info) == 0) {
      dev = (unsigned long long)info.st_dev;
      ino = (unsigned long long)info.st_ino;
    }
#endif
  }
  if (state.actor == 2 && state.overlap && !state.closing &&
      strcmp(event, "exclusive-attempt-return") == 0 && result != 0) {
#ifdef _WIN32
    if (native_error == ERROR_LOCK_VIOLATION) state.failed_exclusive = 1;
#else
    if (native_error == EAGAIN || native_error == EACCES) state.failed_exclusive = 1;
#endif
  }
  /* Native-generated ASCII names only; escape Win namespace backslash. */
  char quoted[128]; size_t j = 0;
  if (name != NULL) {
    for (size_t i = 0; name[i]; ++i) {
      if (j + 3 >= sizeof(quoted)) fatal("trace-name-overflow");
      if (name[i] == '\\' || name[i] == '"') quoted[j++] = '\\';
      quoted[j++] = name[i];
    }
  }
  quoted[j] = 0;
  char line[512];
  int n = snprintf(line, sizeof(line),
    "{\"event\":\"%s\",\"backend\":\"%s\",\"pid\":%ld,\"actor\":%d,"
    "\"seq\":%u,\"ns\":%llu,\"closing\":%d,\"result\":%d,\"os_error\":%lu,"
    "\"errno\":%d,\"exclusive\":%d,\"dev\":%llu,\"ino\":%llu,\"name\":\"%s\"}\n",
    event, BACKEND, own_pid(), state.actor, ++state.count, monotonic_ns(), state.closing,
    result, native_error, nlc_saved_errno, exclusive, dev, ino, quoted);
  if (n <= 0 || n >= (int)sizeof(line) || state.count > 128 ||
      fwrite(line, 1, (size_t)n, state.trace) != (size_t)n || fflush(state.trace)) {
    /* This is a LOGGER/CONTROL failure, never an intended native failure. */
    exit(78);
  }
#ifdef _WIN32
  if (strcmp(event, "reader-mutex-create-return") == 0 ||
      strcmp(event, "writer-mutex-create-return") == 0)
    if (result == 0 && native_error == ERROR_ALREADY_EXISTS) fatal("foreign-name-created-between-checks");
#endif
  NLC_RESTORE;
}
static void fatal(const char *reason) {
  NLC_SAVE;
  if (state.trace != NULL) nlc_event("CONTROL-ERROR", 77, (unsigned long)nlc_saved_os, -1, -1, reason);
  /* Kernel retires own descriptors. No guessed resource cleanup/signals/retry.
   * Named resources may remain on failure: report custody/uncertainty and STOP. */
  exit(77);
}
static void marker_path(char path[4096], const char *marker) {
  int n = snprintf(path, 4096, "%s/%s", state.root, marker);
  if (n <= 0 || n >= 4096) fatal("marker-path-overflow");
}
static void mark(const char *marker) {
  char path[4096]; marker_path(path, marker);
  FILE *stream = fopen(path, "wb");
  if (stream == NULL || fclose(stream)) fatal("marker-write");
}
static int wait_marker(const char *marker) {
  char path[4096], abort_path[4096];
  marker_path(path, marker); marker_path(abort_path, "abort-release");
  unsigned long long now = monotonic_ns();
  if (now == 0) fatal("cooperative-clock-error");
  unsigned long long deadline = now + 15000000000ULL;
  struct stat info;
  for (;;) {
    if (stat(abort_path, &info) == 0) { state.aborted = 1; return 1; }
    if (stat(path, &info) == 0) return 0;
    now = monotonic_ns();
    if (errno != ENOENT || now == 0 || now >= deadline) fatal("cooperative-barrier-deadline");
#ifdef _WIN32
    Sleep(20);
#else
    struct timespec delay = {0, 20000000}; nanosleep(&delay, NULL);
#endif
  }
}

/* Expected absent lookup creates NO handle. Unexpected existing lookup closes
 * its borrowed handle and aborts BEFORE any original initialization/unlink or
 * controlled interval. No diagnostic resource handle is retained in that interval.
 * Access/lookup errors other than precise not-found are NOT absence.
 */
static void require_absent(const char *name) {
#ifdef _WIN32
  HANDLE probe = OpenMutexA(SYNCHRONIZE, FALSE, name);
  DWORD error = GetLastError();
  if (probe != NULL) { CloseHandle(probe); fatal("namespace-already-present"); }
  if (error != ERROR_FILE_NOT_FOUND) fatal("namespace-lookup-error");
#elif defined(__APPLE__)
  sem_t *probe = sem_open(name, 0);
  int error = errno;
  if (probe != SEM_FAILED) { sem_close(probe); fatal("namespace-already-present"); }
  if (error != ENOENT) fatal("namespace-lookup-error");
#else
  (void)name; fatal("unexpected-named-backend-on-linux");
#endif
}
void nlc_namespace(const char *stage, const char *reader, const char *writer) {
  NLC_SAVE;
#ifdef _WIN32
  const char *rp = "Global\\MDBr", *wp = "Global\\MDBw";
#else
  const char *rp = "/MDBr", *wp = "/MDBw";
#endif
  size_t prefix = strlen(rp);
  if (strlen(reader) != prefix + 10 || strlen(writer) != prefix + 10 ||
      strncmp(reader, rp, prefix) || strncmp(writer, wp, prefix) ||
      strcmp(reader + prefix, writer + prefix)) fatal("unexpected-native-name-pair");
  if (strcmp(stage, "init") == 0) {
    require_absent(reader); require_absent(writer);
    strcpy(state.names[0], reader); strcpy(state.names[1], writer);
  } else if (strcmp(stage, "close") == 0) {
    if (strcmp(reader, state.names[0]) || strcmp(writer, state.names[1]))
      fatal("close-target-not-owned-init-pair");
  } else fatal("unknown-namespace-stage");
  nlc_event("namespace-safety-before-originals", 0, (unsigned long)nlc_saved_os, -1, -1, stage);
  NLC_RESTORE;
}
void nlc_close_exclusive(int exclusive) {
  NLC_SAVE;
  if (state.actor == 1 && state.overlap && state.closing && !state.aborted) {
    if (exclusive != 1) fatal("closer-no-exclusive");
    nlc_event("close-exclusive-ready", 0, (unsigned long)nlc_saved_os, exclusive, -1, NULL);
    mark("allow-opener"); wait_marker("shared-attempt-ready");
  }
  NLC_RESTORE;
}
void nlc_shared_attempt_ready(void) {
  NLC_SAVE;
  if (state.actor == 2 && state.overlap && !state.closing) {
    if (!state.failed_exclusive) fatal("shared-without-real-exclusive-failure");
    nlc_event("shared-attempt-ready", 0, (unsigned long)nlc_saved_os, -1, -1, NULL);
    mark("shared-attempt-ready"); /* BEFORE shared syscall; not kernel-blocked proof. */
  }
  NLC_RESTORE;
}
void nlc_windows_named_closed(void) {
  NLC_SAVE;
  if (state.actor == 1 && state.overlap && state.closing && !state.aborted) {
    nlc_event("windows-original-mutexes-closed", 0, (unsigned long)nlc_saved_os, -1, -1, NULL);
    mark("allow-opener"); wait_marker("opener-done");
    /* Original shared file lock still held until native UnlockFile/close follows. */
  }
  NLC_RESTORE;
}

int main(int argc, char **argv) {
  if (argc != 4 || strlen(argv[1]) >= sizeof(state.root) ||
      (strcmp(argv[2], "A") && strcmp(argv[2], "B")) ||
      (strcmp(argv[3], "baseline") && strcmp(argv[3], "interleaved"))) return 64;
  strcpy(state.root, argv[1]); state.actor = strcmp(argv[2], "A") ? 2 : 1;
  state.overlap = strcmp(argv[3], "baseline") != 0;
  char path[4096];
  if (snprintf(path, sizeof(path), "%s/%s.jsonl", state.root, argv[2]) >= (int)sizeof(path)) return 64;
  state.trace = fopen(path, "wb"); if (state.trace == NULL) return 76;
  nlc_event("actor-ready", 0, 0, -1, -1, NULL);
  mark(state.actor == 1 ? "A-ready" : "B-ready");
  if (wait_marker("start")) return 79;
  if (state.actor == 2 && wait_marker("allow-opener")) return 79;
  if (snprintf(path, sizeof(path), "%s/env", state.root) >= (int)sizeof(path)) fatal("env-path-overflow");
  MDB_env *env = NULL;
  int rc = mdb_env_create(&env); if (rc) fatal("env-create");
  rc = mdb_env_set_mapsize(env, 1048576); if (rc) fatal("env-map-size");
  rc = mdb_env_open(env, path, 0, 0600);
  NLC_NOTE("mdb-env-open-return", rc, -1, -1, NULL);
  if (state.actor == 1) {
    if (rc != 0) fatal("closer-initial-open");
    mark("initialized"); wait_marker("begin-close");
#if !defined(_WIN32) && !defined(__APPLE__)
    /* Actual default POSIX mutex backend has NO close-exclusive/SEM hook.
     * Meaningful legal overlap: A stays OPEN while B opens and closes using
     * actual failed-exclusive/shared-acquisition protocol; both must succeed. */
    if (state.overlap && !state.aborted) {
      nlc_event("linux-live-env-overlap", 0, 0, -1, -1, NULL);
      mark("allow-opener"); wait_marker("opener-done");
    }
#endif
  }
  state.closing = 1;
  NLC_NOTE("env-close-enter", 0, -1, -1, NULL);
  mdb_env_close(env); /* Original successful OR failed-open handle, exactly once. */
  NLC_NOTE("env-close-return", rc, -1, -1, NULL);
  if (state.actor == 2) mark("opener-done");
  else {
    if (!state.overlap && !state.aborted) mark("allow-opener");
    if (!state.aborted) wait_marker("opener-done");
    if (state.names[0][0]) {
      require_absent(state.names[0]); require_absent(state.names[1]);
      nlc_event("owned-names-retired", 0, 0, -1, -1, NULL);
    }
  }
  printf("{\"actor\":%d,\"pid\":%ld,\"backend\":\"%s\",\"open_rc\":%d,\"env_closed\":true}\n",
         state.actor, own_pid(), BACKEND, rc);
  fclose(state.trace);
  return state.aborted ? 79 : 0; /* Abort NEVER an intended mechanism pass. */
}
