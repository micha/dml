project(
  'dml',
  'c',
  version: '0.1.0',
  meson_version: '>=1.4',
  default_options: ['c_std=c11', 'warning_level=3'],
)

xxhash_proj = subproject('xxhash')
lmdb_proj = subproject('lmdb')
utf8proc_proj = subproject('utf8proc')
uriparser_proj = subproject('uriparser')

vendor_libraries = [
  xxhash_proj.get_variable('libxxhash'),
  lmdb_proj.get_variable('liblmdb'),
  utf8proc_proj.get_variable('utf8proc_lib'),
  uriparser_proj.get_variable('uriparser_lib'),
]
vendor_headers = []
foreach dep : [
  xxhash_proj.get_variable('xxhash_dep'),
  lmdb_proj.get_variable('lmdb_dep'),
  utf8proc_proj.get_variable('utf8proc_dep'),
  uriparser_proj.get_variable('uriparser_dep'),
]
  vendor_headers += [dep.partial_dependency(compile_args: true, includes: true)]
endforeach

threads_dep = dependency('threads')
dml_inc = include_directories('include')

libdml = static_library(
  'dml',
  files(
    'src/dml.c',
    'src/encoding.c',
    'src/error.c',
    'src/object.c',
    'src/object_id.c',
    'src/record.c',
    'src/repo.c',
    'src/text.c',
    'src/uri.c',
  ),
  include_directories: dml_inc,
  # Install a complete archive without requiring separate vendor libraries.
  link_whole: vendor_libraries,
  dependencies: vendor_headers + [threads_dep],
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
  dependencies: threads_dep,
)
meson.override_dependency('dml', dml_dep)

if get_option('quint_tests')
  python = find_program('python3', version: '>=3.10')
  quint = find_program('quint')
  ref_replay = executable('ref_replay', 'tests/ref_replay.c', dependencies: dml_dep)
  lmdb_inventory = executable(
    'lmdb_inventory', 'tests/lmdb_inventory.c',
    dependencies: lmdb_proj.get_variable('lmdb_dep'),
  )
  test(
    'quint-create-ref', python,
    args: [files('tests/run_ref_create.py'), quint.full_path(), ref_replay, lmdb_inventory,
           files('tests/ref_histories.qnt', 'tests/ref_rules.qnt')],
    timeout: 90,
  )
endif
