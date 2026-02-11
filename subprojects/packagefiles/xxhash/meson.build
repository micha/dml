project(
  'xxhash',
  'c',
  default_options: [
    'c_std=c11',
    'default_library=static',
  ],
)

xxhash_inc = include_directories('.')

libxxhash = static_library(
  'xxhash',
  'xxhash.c',
  include_directories: xxhash_inc,
)

xxhash_dep = declare_dependency(
  link_with: libxxhash,
  include_directories: xxhash_inc,
)
