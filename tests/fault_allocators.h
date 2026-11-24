#ifndef DML_TEST_FAULT_ALLOCATORS_H
#define DML_TEST_FAULT_ALLOCATORS_H

#include <stdlib.h>

/* These macros name our substitutes in the instrumented test builds only.
 * Some C runtimes (including MinGW) undefine them while declaring the real
 * allocators, so declare the substituted names separately. */
#ifdef malloc
void *malloc(size_t size);
#endif
#ifdef calloc
void *calloc(size_t count, size_t size);
#endif
#ifdef realloc
void *realloc(void *ptr, size_t size);
#endif

#endif
