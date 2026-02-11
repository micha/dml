#include <stdio.h>
#include <string.h>

#include "dml/dml.h"

static int print_usage(const char *argv0) {
  fprintf(stderr, "usage: %s [--version|-V]\n", argv0);
  return 2;
}

int main(int argc, char **argv) {
  if (argc == 1) {
    return print_usage(argv[0]);
  }

  if ((strcmp(argv[1], "--version") == 0) || (strcmp(argv[1], "-V") == 0)) {
    if (argc != 2) {
      return print_usage(argv[0]);
    }

    puts(dml_version());
    return 0;
  }

  return print_usage(argv[0]);
}
