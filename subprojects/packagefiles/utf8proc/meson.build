project('utf8proc', 'c', version: '2.11.3', default_options: ['c_std=c11', 'default_library=static'])

utf8proc_lib = static_library(
  'utf8proc',
  'utf8proc.c',
  include_directories: include_directories('.'),
  c_args: ['-DUTF8PROC_STATIC'],
)

utf8proc_dep = declare_dependency(
  link_with: utf8proc_lib,
  include_directories: include_directories('.'),
  compile_args: ['-DUTF8PROC_STATIC'],
)
