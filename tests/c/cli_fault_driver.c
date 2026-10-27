/* Private CLI fault executable: same maintained source, never installed. */
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>

#include "fault_injection.h"

static long write_nth;
static int fail_write(void) {
  if (write_nth > 0 && --write_nth == 0) { errno = EIO; return 1; }
  return 0;
}
static int test_fputs(const char *s, FILE *stream) { return fail_write() ? EOF : fputs(s, stream); }
static int test_putchar(int c) { return fail_write() ? EOF : putchar(c); }
static int test_puts(const char *s) { return fail_write() ? EOF : puts(s); }
static int test_fflush(FILE *stream) { return fail_write() ? EOF : fflush(stream); }
static size_t test_fwrite(const void *data, size_t size, size_t n, FILE *stream) {
  return fail_write() ? 0 : fwrite(data, size, n, stream);
}
static int test_fprintf(FILE *stream, const char *format, ...) {
  if (fail_write()) return EOF;
  va_list args; va_start(args, format); int result = vfprintf(stream, format, args); va_end(args);
  return result;
}
#define fputs test_fputs
#define putchar test_putchar
#define puts test_puts
#define fflush test_fflush
#define fwrite test_fwrite
#define fprintf test_fprintf
#define main cli_main
#include "../../src/cli.c"
#undef main

int main(int argc, char **argv) {
  if (argc < 4) return 2;
  if (atoi(argv[1]) == 4) {
    Text text = {0};
    if (grow(&text, SIZE_MAX)) { free(text.data); return 1; }
    text = (Text){0};
    raw(&text, "z", 1);
    if (grow(&text, SIZE_MAX - 1)) { free(text.data); return 1; }
    free(text.data);
    text = (Text){0};
    for (size_t i = 0; i < 2050; i++) {
      raw(&text, "x", 1);
      if (text.failed || text.len != i + 1 || text.capacity < text.len + 1 ||
          text.data[i] != 'x' || text.data[text.len] != '\0') {
        free(text.data);
        return 1;
      }
    }
    free(text.data);
    return 0;
  }
  if (atoi(argv[1]) == 1) dml_test_fail(DML_TEST_ALLOCATE, (size_t)atol(argv[2]), 0);
  else if (atoi(argv[1]) == 3) dml_test_hash_collision(1);
  else write_nth = atol(argv[2]);
  return cli_main(argc - 2, argv + 2);
}
