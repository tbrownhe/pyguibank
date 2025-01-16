# pyguibank

## For Developers

### Creating an updated development environment
This installs the most recent versions of all packages in conda-forge and PyPI.
- `conda env create -f dev_environment.yml`

### Creating a replica of the dev environment of the last working release
This installs the exact versions of all dependencies in the last stable build of PyGuiBank.
- `conda env create -f build_env_{platform}.yml`

### Saving a release requirements snapshot
This stores the exact versions of all dependencies for a stable build of PyGuiBank.
- `conda env export > build_env_{platform}.yml`

### Updating installed packages while maintaining dev_environment constraints
1. `conda update --all`
2. `pip list --outdated`
3. For each outdated pip package run `pip install --upgrade package-name`


## Plugin Manager

The modules located in src\plugins can be located anywhere. This is designed to allow plugins to be distributed to end-users without a new version of the app and to potentially enable a subscription-like service. Their path does not need to follow pythonic directory structure. They are only located in src/plugins so that an IDE can predict any import issues.

### How it works
1. Run `python -m compileall plugins` to create compiled `.pyc` files in `__pycache__` directories. Or run `compileall.compile_dir("src/plugins", force=True)` from within python.
2. Copy the `.pyc` files anywhere. They must remain in their respective pdf, csv, xlsx, etc folder, but the `__pycache__` directory is unnecessary.
3. When calling `PluginManager.preload_plugins(plugin_path)`, ensure `plugin_path` points to the plugins directory.
4. Even though the `.pyc` files are not located relative to the project directory, they are imported in a way that treats them as if they are located in \src\plugins
5. In the .db file StatementTypes.EntryPoint column, the location of the plugin is given like `plugins.pdf.capitaloneauto:Parser` where `plugins.pdf.capitaloneauto` is the module name, and `Parser` is the class name to import from the module to parse the incoming data. 

## Deployment
1. Run `build_pyguibank.bat`.
    - This compiles all current plugins and moves them to `dist\plugins`.
    - Then PyInstaller runs and includes all necessary files in the release.
    - Finally, NSIS packages the compiled app into an installer at `dist\pyguibank_version_setup.exe`
2. All `.pyc` files are now plugin files.
3. Run PyInstaller with a `--add-data "dist\plugins;plugins"` flag to include all current plugins.
4. Any new plugins can be distributed to users without needing another version of the app, as long as imports from core.utils, core.validation, and core.interface stay the same. They just need to add the corresponding `.pyc` file to the plugin manager system and add a line in the database StatementTypes table to map to the plugin.