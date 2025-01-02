# pyguibank

### Creating an updated development environment
This installs the most recent versions of all packages in conda-forge and PyPI.
- `conda env create -f dev_environment.yml`

### Creating a replica of the dev environment of the last working release
This installs the exact versions of all dependencies in the last stable build of PyGuiBank.
- `conda env create -f release_requirements.yml`

### Saving a release requirements snapshot
This stores the exact versions of all dependencies for a stable build of PyGuiBank.
- `conda env export > release_requirements.yml`

### Updating installed packages while maintaining dev_environment constraints
1. `conda update --all`
2. `pip list --outdated`
3. For each outdated pip package run `pip install --upgrade package-name`
