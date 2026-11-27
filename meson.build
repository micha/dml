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

if get_option('python_bindings') or get_option('quint_tests')
  python = import('python').find_installation(pure: false)
  if not python.language_version().version_compare('>=3.10')
    error('DML Python bindings require CPython 3.10 or newer')
  endif
  python_dep = python.dependency()
  subdir('python/daggerml')
endif

if get_option('quint_tests')
  quint_script = get_option('quint_script')
  quint_args = []
  if quint_script == ''
    quint = find_program('quint')
  else
    quint = find_program(build_machine.system() == 'windows' ? 'node.exe' : 'node')
    quint_script = meson.project_source_root() / quint_script
    if not import('fs').is_file(quint_script)
      error('Quint JavaScript entry point not found: ' + quint_script)
    endif
    quint_args = ['--quint-script', quint_script]
  endif
  trace_interpreter = files('tests/run_histories.py')
  test('trace-interpreter', python, args: ['-B', files('tests/test_trace_interpreter.py')])
  private_python_core = python.extension_module(
    '_dml_core', 'python/dml_core.c',
    c_args: ['-DDML_PRIVATE_REPLAY'],
    dependencies: [python_dep, dml_dep],
    install: false,
  )
  binding_env = environment()
  binding_env.prepend('PYTHONPATH', meson.current_build_dir() / 'python')
  test(
    'python-binding', python,
    args: ['-B', files('tests/test_python_binding.py')],
    env: binding_env,
    depends: public_python_core,
  )
  test(
    'recorded-calls-boundaries', python,
    args: ['-B', files('tests/test_recorded_calls.py')],
    env: binding_env,
    depends: public_python_core,
    # Suite budget for many CLI launches; Python still bounds each subprocess.
    timeout: 90,
  )
  lmdb_inventory = executable(
    'lmdb_inventory', 'tests/lmdb_inventory.c',
    dependencies: lmdb_proj.get_variable('lmdb_dep'),
  )
  # Includes history loading and live replay in addition to Quint verdicts.
  # Keep headroom above the Intel macOS verdict timeout in run_histories.py.
  intel_macos = host_machine.system() == 'darwin' and host_machine.cpu_family() == 'x86_64'
  replay_timeout = intel_macos ? 330 : 210
  test(
    'quint-refs', python,
    args: ['-B', trace_interpreter, quint.full_path(), 'daggerml.core', lmdb_inventory,
           files('tests/ref_histories.qnt', 'tests/ref_rules.qnt'), '--init', 'init', '--init', 'changedInit'] + quint_args,
    env: binding_env,
    depends: public_python_core,
    timeout: replay_timeout,
  )
  retention_modules = ['--quint-module', files('tests/retention_fixture.qnt'),
                       '--quint-module', files('tests/retention_rules.qnt')]
  foreach suite : [
    ['transfer', 'transfer', ['--quint-module', files('tests/transfer_fixture.qnt')]],
    ['staged-import', 'staged_import', retention_modules],
    ['gc', 'gc', retention_modules],
  ]
    test(
      'quint-' + suite[0], python,
      args: ['-B', trace_interpreter, quint.full_path(), private_python_core, lmdb_inventory,
             files('tests/' + suite[1] + '_histories.qnt', 'tests/' + suite[1] + '_rules.qnt')] + suite[2] + quint_args,
      timeout: replay_timeout,
    )
  endforeach

  # Instrument the test copies only, never the installed library.
  fault_header = meson.current_source_dir() / 'tests/fault_allocators.h'
  force_fault_header = ['-include', fault_header]
  if meson.get_compiler('c').get_argument_syntax() == 'msvc'
    force_fault_header = ['/FI' + fault_header]
  endif
  repo_check_fault_subject = static_library(
    'repo_check_fault_subject', 'src/repo_check.c', 'src/object_id.c', 'src/repo.c',
    include_directories: dml_inc,
    dependencies: vendor_headers,
    c_args: ['-Dmalloc=dml_check_fault_malloc', '-Drealloc=dml_check_fault_realloc',
             '-Dmdb_del=dml_check_fault_del'] + force_fault_header,
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

  provenance_handoff = executable(
    'provenance_handoff', 'examples/provenance_handoff.c',
    dependencies: dml_dep,
  )
  handoff_fixture = executable(
    'handoff_fixture', 'tests/handoff_fixture.c',
    dependencies: dml_dep,
  )
  test(
    'provenance-handoff', python,
    args: ['-B', files('tests/run_provenance_handoff.py'), quint.full_path(), provenance_handoff, handoff_fixture,
           files('tests/handoff_histories.qnt', 'tests/handoff_rules.qnt')] + quint_args,
    timeout: replay_timeout,
  )

  recorded_calls_modules = files('tests/recorded_calls_fixtures.qnt', 'tests/recorded_calls_stored_histories.qnt',
                                 'tests/recorded_calls_outbound_histories.qnt')
  test(
    'recorded-calls', python,
    args: ['-B', files('tests/run_recorded_calls.py'), quint.full_path(),
           files('examples/recorded_calls.py', 'tests/recorded_calls_histories.qnt', 'tests/recorded_calls_rules.qnt')]
          + recorded_calls_modules + quint_args,
    env: binding_env,
    depends: public_python_core,
    timeout: replay_timeout,
  )

  # Keep the durable plan/receipt verdict input separate to bound replay time.
  test(
    'recorded-calls-durable', python,
    args: ['-B', files('tests/run_recorded_calls.py'), quint.full_path(),
           files('examples/recorded_calls.py', 'tests/recorded_calls_durable_histories.qnt',
                 'tests/recorded_calls_durable_rules.qnt', 'tests/recorded_calls_histories.qnt',
                 'tests/recorded_calls_rules.qnt', 'tests/recorded_calls_plan_histories.qnt',
                 'tests/recorded_calls_plan_rules.qnt', 'tests/recorded_calls_receipt_histories.qnt',
                 'tests/recorded_calls_receipt_rules.qnt')] + recorded_calls_modules + quint_args,
    env: binding_env,
    depends: public_python_core,
    timeout: replay_timeout,
  )

  # These verdicts are wide. Keep the extra Quint evaluators out of parallel
  # replay (the main recorded-calls suite timed out on Windows).
  adoption_fixture_modules = files('tests/recorded_calls_adoption_fixture.qnt', 'tests/recorded_calls_adoption_checks.qnt')
  foreach suite : ['reuse', 'selection', 'adoption', 'policy', 'intent', 'supersession', 'supersession-invalid',
                   'table-capacity', 'table-scope', 'intent-table-edit', 'intent-table-route']
    extra_modules = []
    if suite in ['adoption', 'intent', 'supersession-invalid']
      extra_modules += adoption_fixture_modules
    endif
    if suite == 'adoption'
      extra_modules += files('tests/recorded_calls_adoption_validation.qnt')
    elif suite == 'supersession-invalid'
      extra_modules += files('tests/recorded_calls_intent_histories.qnt', 'tests/recorded_calls_intent_rules.qnt')
    elif suite in ['table-capacity', 'table-scope', 'intent-table-edit', 'intent-table-route']
      extra_modules += files('tests/recorded_calls_table_fixture.qnt')
      if suite == 'intent-table-edit'
        extra_modules += files('tests/recorded_calls_table_capacity_histories.qnt')
      endif
    endif
    module_suffix = suite.replace('-', '_')
    test(
      'recorded-calls-' + suite, python,
      args: ['-B', files('tests/run_recorded_calls.py'), quint.full_path(),
             files('examples/recorded_calls.py', 'tests/recorded_calls_' + module_suffix + '_histories.qnt',
                   'tests/recorded_calls_' + module_suffix + '_rules.qnt', 'tests/recorded_calls_histories.qnt',
                   'tests/recorded_calls_rules.qnt')] + recorded_calls_modules + extra_modules + quint_args,
      env: binding_env,
      depends: public_python_core,
      is_parallel: false,
      timeout: replay_timeout,
    )
  endforeach

  test(
    'argument-map-trace', python,
    args: ['-B', files('tests/run_argument_maps.py'), quint.full_path(),
           files('examples/recorded_argument_maps.py'), lmdb_inventory,
           files('tests/argument_map_trace_histories.qnt', 'tests/argument_map_trace_rules.qnt'), '--native'] + quint_args,
    env: binding_env,
    depends: public_python_core,
    is_parallel: false,
    timeout: replay_timeout,
  )
  test(
    'argument-maps', python,
    args: ['-B', files('tests/run_argument_maps.py'), quint.full_path(),
           files('examples/recorded_argument_maps.py'), lmdb_inventory,
           files('tests/argument_maps_histories.qnt', 'tests/argument_maps_rules.qnt')] + quint_args,
    env: binding_env,
    depends: public_python_core,
    timeout: replay_timeout,
  )

  # Check the larger returned-source graph separately so its observations do not
  # share Quint's evidence evaluation deadline with the other argument-map histories.
  test(
    'argument-map-budget', python,
    args: ['-B', files('tests/run_argument_maps.py'), quint.full_path(),
           files('examples/recorded_argument_maps.py'), lmdb_inventory,
           files('tests/argument_map_budget_histories.qnt', 'tests/argument_map_budget_rules.qnt')] + quint_args,
    env: binding_env,
    depends: public_python_core,
    timeout: replay_timeout,
  )

  test(
    'argument-map-poison', python,
    args: ['-B', files('tests/run_argument_map_poison.py'), quint.full_path(),
           files('examples/recorded_argument_maps.py'), lmdb_inventory,
           files('tests/argument_map_poison_histories.qnt', 'tests/argument_map_poison_rules.qnt')] + quint_args,
    env: binding_env,
    depends: public_python_core,
    timeout: replay_timeout,
  )

  test(
    'argument-map-request-integrity', python,
    args: ['-B', files('tests/run_argument_map_request_integrity.py'), quint.full_path(),
           files('examples/recorded_argument_maps.py'), lmdb_inventory,
           files('tests/argument_map_request_integrity_histories.qnt',
                 'tests/argument_map_request_integrity_rules.qnt')] + quint_args,
    env: binding_env,
    depends: public_python_core,
    timeout: replay_timeout,
  )

  test(
    'argument-map-returned-source', python,
    args: ['-B', files('tests/run_argument_map_returned_source.py'), quint.full_path(),
           files('examples/recorded_argument_maps.py'), lmdb_inventory,
           files('tests/argument_map_returned_source_histories.qnt',
                 'tests/argument_map_returned_source_rules.qnt')] + quint_args,
    env: binding_env,
    depends: public_python_core,
    timeout: replay_timeout,
  )

  test(
    'builtins-boundaries', python,
    args: ['-B', files('tests/test_builtins.py')],
    env: binding_env,
    depends: public_python_core,
  )
  test(
    'recorded-builtins', python,
    args: ['-B', files('tests/run_builtins.py'), quint.full_path(),
           files('examples/recorded_builtins.py'), lmdb_inventory,
           files('tests/builtins_histories.qnt', 'tests/builtins_rules.qnt')] + quint_args,
    env: binding_env,
    depends: public_python_core,
    timeout: replay_timeout,
  )

  test(
    'recorded-composition', python,
    args: ['-B', files('tests/run_composition.py'), quint.full_path(),
           files('examples/recorded_composition.py'), lmdb_inventory,
           files('tests/composition_histories.qnt', 'tests/composition_rules.qnt')] + quint_args,
    env: binding_env,
    depends: public_python_core,
    timeout: replay_timeout,
  )

  test(
    'ordinary-call-boundaries', python,
    args: ['-B', files('tests/test_ordinary_calls.py'), lmdb_inventory],
    env: binding_env,
    depends: public_python_core,
  )
  test(
    'closure-boundaries', python,
    args: ['-B', files('tests/test_closures.py'), lmdb_inventory],
    env: binding_env,
    depends: public_python_core,
  )
  test(
    'recorded-closures', python,
    args: ['-B', files('tests/run_closures.py'), quint.full_path(),
           files('examples/recorded_closures.py'), lmdb_inventory,
           files('tests/closure_histories.qnt', 'tests/closure_rules.qnt')] + quint_args,
    env: binding_env,
    depends: public_python_core,
    timeout: replay_timeout,
  )

  test(
    'recorded-ordinary-calls', python,
    args: ['-B', files('tests/run_ordinary_calls.py'), quint.full_path(),
           files('examples/recorded_ordinary_calls.py'), lmdb_inventory,
           files('tests/ordinary_histories.qnt', 'tests/ordinary_rules.qnt')] + quint_args,
    env: binding_env,
    depends: public_python_core,
    timeout: replay_timeout,
  )

  test(
    'call-scope-boundaries', python,
    args: ['-B', files('tests/test_calls.py')],
    env: binding_env,
    depends: public_python_core,
  )
  test(
    'implementation-bound-calls', python,
    args: ['-B', files('tests/run_implementation_bound.py'), quint.full_path(),
           files('examples/recorded_ordinary_calls.py'), lmdb_inventory,
           files('tests/implementation_bound_histories.qnt', 'tests/implementation_bound_rules.qnt')] + quint_args,
    env: binding_env,
    depends: public_python_core,
    timeout: replay_timeout,
  )

  transfer_fault_subject = static_library(
    'transfer_fault_subject', 'src/transfer.c', 'src/object.c',
    include_directories: dml_inc,
    dependencies: vendor_headers,
    c_args: ['-Dmalloc=dml_fault_malloc', '-Dcalloc=dml_fault_calloc', '-Drealloc=dml_fault_realloc'] +
            force_fault_header,
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
