package_init = configure_file(input: '__init__.py', output: '__init__.py', copy: true)
public_python_core = python.extension_module(
  'core', '../dml_core.c',
  dependencies: [python_dep, dml_dep],
  subdir: 'daggerml',
  install: get_option('python_bindings'),
  install_tag: 'python-runtime',
)
if get_option('python_bindings')
  python.install_sources(package_init, subdir: 'daggerml', install_tag: 'python-runtime')
endif
