project('uriparser', 'c', version: '1.0.2', default_options: ['c_std=c11', 'default_library=static'])

uriparser_sources = files(
  'src/UriCommon.c',
  'src/UriCompare.c',
  'src/UriCopy.c',
  'src/UriEscape.c',
  'src/UriFile.c',
  'src/UriIp4.c',
  'src/UriIp4Base.c',
  'src/UriMemory.c',
  'src/UriNormalize.c',
  'src/UriNormalizeBase.c',
  'src/UriParse.c',
  'src/UriParseBase.c',
  'src/UriQuery.c',
  'src/UriRecompose.c',
  'src/UriResolve.c',
  'src/UriSetFragment.c',
  'src/UriSetHostAuto.c',
  'src/UriSetHostCommon.c',
  'src/UriSetHostIp4.c',
  'src/UriSetHostIp6.c',
  'src/UriSetHostIpFuture.c',
  'src/UriSetHostRegName.c',
  'src/UriSetPath.c',
  'src/UriSetPort.c',
  'src/UriSetQuery.c',
  'src/UriSetScheme.c',
  'src/UriSetUserInfo.c',
  'src/UriShorten.c',
  'src/UriVersion.c',
)

uriparser_lib = static_library(
  'uriparser',
  uriparser_sources,
  include_directories: include_directories('include'),
  c_args: ['-DURI_LIBRARY_BUILD', '-DURI_STATIC_BUILD', '-DURI_NO_UNICODE'],
)

uriparser_dep = declare_dependency(
  link_with: uriparser_lib,
  include_directories: include_directories('include'),
  compile_args: ['-DURI_STATIC_BUILD', '-DURI_NO_UNICODE'],
)
