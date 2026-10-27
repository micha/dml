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

utf8proc_proj = subproject('utf8proc', default_options: ['default_library=static'])
utf8proc_dep = utf8proc_proj.get_variable('utf8proc_dep')

uriparser_proj = subproject('uriparser', default_options: ['default_library=static'])
uriparser_dep = uriparser_proj.get_variable('uriparser_dep')

dml_inc = include_directories('include')

dml_sources = files(
  'src/dml.c',
  'src/encoding.c',
  'src/error.c',
  'src/object.c',
  'src/object_id.c',
  'src/record.c',
  'src/repo.c',
  'src/text.c',
  'src/uri.c',
)

libdml = static_library(
  'dml',
  dml_sources,
  include_directories: dml_inc,
  dependencies: [xxhash_dep, lmdb_dep, utf8proc_dep, uriparser_dep],
  install: true,
)

install_headers(
  'include/dml/dml.h',
  'include/dml/error.h',
  'include/dml/object.h',
  'include/dml/record.h',
  'include/dml/repo.h',
  subdir: 'dml',
)

dml_dep = declare_dependency(
  link_with: libdml,
  include_directories: dml_inc,
  dependencies: [xxhash_dep, lmdb_dep, utf8proc_dep, uriparser_dep],
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

test_record = executable(
  'test_record',
  'tests/c/test_record.c',
  include_directories: dml_inc,
  dependencies: dml_dep,
)

test('test_record', test_record)

test_record_failure = executable(
  'test_record_failure',
  'tests/c/test_record_failure.c',
  include_directories: dml_inc,
  dependencies: dml_dep,
)

test('test_record_failure', test_record_failure)

test_repo = executable(
  'test_repo',
  'tests/c/test_repo.c',
  include_directories: dml_inc,
  dependencies: dml_dep,
)

test('test_repo', test_repo, is_parallel: false)

test_core_driver = executable(
  'test_core_driver',
  'tests/c/core_driver.c',
  include_directories: dml_inc,
  dependencies: dml_dep,
)

test_object = executable(
  'test_object', 'tests/c/test_object.c',
  include_directories: dml_inc, dependencies: dml_dep,
)
test('test_object', test_object)

executable(
  'test_history_driver', 'tests/c/history_driver.c',
  include_directories: dml_inc, dependencies: dml_dep,
)

boundary_test = executable(
  'test_boundaries', 'tests/c/test_boundaries.c',
  include_directories: dml_inc, dependencies: dml_dep,
)
test('test_boundaries', boundary_test)

# Compile the same sources with dependency-call substitution only in this
# private test core. The installed library has no hooks or mutable fault state.
fault_core = static_library(
  'dml_test_fault_core', dml_sources,
  include_directories: dml_inc,
  dependencies: [xxhash_dep, lmdb_dep, utf8proc_dep, uriparser_dep],
  c_args: ['-include', meson.current_source_dir() / 'tests/c/fault_injection.h'],
  install: false,
)
fault_test = executable(
  'test_faults', 'tests/c/test_faults.c', 'tests/c/fault_injection.c',
  include_directories: dml_inc,
  link_with: fault_core,
  dependencies: [xxhash_dep, lmdb_dep, utf8proc_dep, uriparser_dep],
)
test('test_faults', fault_test, is_parallel: false)

meson.override_dependency('dml', dml_dep)
