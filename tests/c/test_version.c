#include <stdio.h>
#include <string.h>

#include "dml/dml.h"

int main(void) {
  const char *version = dml_version();

  if (version == NULL) {
    fprintf(stderr, "dml_version returned NULL\n");
    return 1;
  }

  if (strcmp(version, DML_VERSION) != 0) {
    fprintf(stderr, "unexpected version: %s\n", version);
    return 1;
  }

  return 0;
}
