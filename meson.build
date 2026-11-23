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
    'src/repo_check.c',
    'src/text.c',
    'src/transfer.c',
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
  'include/dml/transfer.h',
  subdir: 'dml',
)

dml_dep = declare_dependency(
  link_with: libdml,
  include_directories: dml_inc,
  dependencies: threads_dep,
)
meson.override_dependency('dml', dml_dep)

if get_option('quint_tests')
  python = import('python').find_installation('python3')
  if not python.language_version().version_compare('>=3.10')
    error('Quint checks require CPython 3.10 or newer')
  endif
  quint = find_program('quint')
  trace_interpreter = files('tests/run_histories.py')
  test('trace-interpreter', python, args: ['-B', files('tests/test_trace_interpreter.py')])
  python_core = python.extension_module(
    '_dml_core', 'python/dml_core.c',
    dependencies: [python.dependency(), dml_dep],
    install: false,
  )
  lmdb_inventory = executable(
    'lmdb_inventory', 'tests/lmdb_inventory.c',
    dependencies: lmdb_proj.get_variable('lmdb_dep'),
  )
  retention_modules = ['--quint-module', files('tests/retention_fixture.qnt'),
                       '--quint-module', files('tests/retention_rules.qnt')]
  foreach suite : [
    ['refs', 'ref', ['--init', 'init', '--init', 'changedInit']],
    ['transfer', 'transfer', ['--quint-module', files('tests/transfer_fixture.qnt')]],
    ['staged-import', 'staged_import', retention_modules],
    ['gc', 'gc', retention_modules],
  ]
    test(
      'quint-' + suite[0], python,
      args: ['-B', trace_interpreter, quint.full_path(), python_core, lmdb_inventory,
             files('tests/' + suite[1] + '_histories.qnt', 'tests/' + suite[1] + '_rules.qnt')] + suite[2],
      timeout: 150,
    )
  endforeach

  # Instrument the test copies only, never the installed library.
  repo_check_fault_subject = static_library(
    'repo_check_fault_subject', 'src/repo_check.c', 'src/object_id.c', 'src/repo.c',
    include_directories: dml_inc,
    dependencies: vendor_headers,
    c_args: ['-Dmalloc=dml_check_fault_malloc', '-Drealloc=dml_check_fault_realloc',
             '-Dmdb_del=dml_check_fault_del'],
  )
  repo_check = executable(
    'repo_check', 'tests/repo_check.c',
    objects: repo_check_fault_subject.extract_all_objects(recursive: false),
    dependencies: [dml_dep, lmdb_proj.get_variable('lmdb_dep')],
  )
  test(
    'native-repo-integrity', python,
    args: ['-c', '''
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    subprocess.run([sys.argv[1], Path(tmp)], check=True)
''', repo_check],
  )

  transfer_boundaries = executable(
    'transfer_boundaries', 'tests/transfer_boundaries.c',
    dependencies: [dml_dep, lmdb_proj.get_variable('lmdb_dep')],
  )
  test(
    'native-transfer-boundaries', python,
    args: ['-c', '''
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    subprocess.run([sys.argv[1], *(Path(tmp) / name for name in ('source', 'oversize', 'dest'))], check=True)
''', transfer_boundaries],
  )

  transfer_fault_subject = static_library(
    'transfer_fault_subject', 'src/transfer.c', 'src/object.c',
    include_directories: dml_inc,
    dependencies: vendor_headers,
    c_args: ['-Dmalloc=dml_fault_malloc', '-Dcalloc=dml_fault_calloc', '-Drealloc=dml_fault_realloc'],
  )
  transfer_faults = executable(
    'transfer_faults', 'tests/transfer_faults.c',
    objects: transfer_fault_subject.extract_all_objects(recursive: false),
    dependencies: dml_dep,
  )
  test(
    'native-transfer-faults', python,
    args: ['-c', '''
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    subprocess.run([sys.argv[1], Path(tmp) / 'source', Path(tmp) / 'dest'], check=True)
''', transfer_faults],
  )
endif
