pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'assistant'

gnome = import('gnome')
python = import('python')

blueprint_compiler = find_program('blueprint-compiler', required: true)

blueprint_files = files(
  'window.blp',
  'message_item.blp',
  'gtk/help-overlay.blp',
)

compiled_ui_dir_name = 'compiled_ui_files'

compiled_blueprints = custom_target('compiled_blueprints',
  input: blueprint_files,
  output: compiled_ui_dir_name,
  command: [blueprint_compiler, 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@']
)

gnome.compile_resources('assistant',
  'assistant.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
  dependencies: [compiled_blueprints],
  source_dir: [meson.current_source_dir(), compiled_blueprints.full_path()],
)

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'assistant.in',
  output: 'assistant',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x'
)

assistant_sources = [
  '__init__.py',
  'main.py',
  'window.py',
  'commands.py',
  'message_item.py',
  'window_actions.py',
  'style.css',
  'style-dark.css',
]

install_data(assistant_sources, install_dir: moduledir)
