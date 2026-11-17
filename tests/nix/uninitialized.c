/* Intentional Memcheck failure: the Nix check must observe exit 101. */
#include <stdio.h>
#include <stdlib.h>

int main(void) {
  unsigned char *value = malloc(1);
  if (value == NULL) {
    return 2;
  }
  if (*value == 0) {
    puts("zero");
  } else {
    puts("nonzero");
  }
  free(value);
  return 0;
}
