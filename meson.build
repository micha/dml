project(
  'dml',
  'c',
  version: '0.1.0',
  default_options: [
    'c_std=c11',
    'default_library=static',
    'warning_level=3',
  ],
)

xxhash_proj = subproject('xxhash', default_options: ['default_library=static'])
xxhash_dep = xxhash_proj.get_variable('xxhash_dep')

lmdb_proj = subproject('lmdb', default_options: ['default_library=static'])
lmdb_dep = lmdb_proj.get_variable('lmdb_dep')

dml_inc = include_directories('include')

libdml = static_library(
  'dml',
  'src/dml.c',
  include_directories: dml_inc,
  dependencies: [xxhash_dep, lmdb_dep],
  install: true,
)

install_headers('include/dml/dml.h', subdir: 'dml')

dml_dep = declare_dependency(
  link_with: libdml,
  include_directories: dml_inc,
  dependencies: [xxhash_dep, lmdb_dep],
)

dml_cli = executable(
  'dml',
  'src/cli.c',
  include_directories: dml_inc,
  dependencies: dml_dep,
  install: true,
)

test_version = executable(
  'test_version',
  'tests/c/test_version.c',
  include_directories: dml_inc,
  dependencies: dml_dep,
)

test('test_version', test_version)

meson.override_dependency('dml', dml_dep)
