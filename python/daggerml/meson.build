project('daggerml', 'c', version: '0.1.0', default_options: ['c_std=c11'])

py = import('python').find_installation(pure: false)
py_dep = py.dependency()

dml_core = static_library(
  'dmlcore',
  [
    'src/_core_module.c',
  ],
  include_directories: include_directories('src'),
  dependencies: [py_dep],
  install: false,
)

py.extension_module(
  '_core',
  [],
  link_with: dml_core,
  dependencies: [py_dep],
  subdir: 'daggerml',
  install: true,
  limited_api: '3.8',
)

py.install_sources(
  [
    'daggerml/__init__.py',
    'daggerml/_core.pyi',
    'daggerml/py.typed',
  ],
  subdir: 'daggerml',
)
