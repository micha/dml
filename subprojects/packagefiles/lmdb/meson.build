project(
  'lmdb',
  'c',
  default_options: [
    'c_std=c11',
    'default_library=static',
  ],
)

lmdb_inc = include_directories('libraries/liblmdb')
threads_dep = dependency('threads')

liblmdb = static_library(
  'lmdb',
  [
    'libraries/liblmdb/mdb.c',
    'libraries/liblmdb/midl.c',
  ],
  include_directories: lmdb_inc,
  dependencies: threads_dep,
)

lmdb_dep = declare_dependency(
  link_with: liblmdb,
  include_directories: lmdb_inc,
  dependencies: threads_dep,
)
