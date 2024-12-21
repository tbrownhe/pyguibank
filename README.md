# pyguibank

### Creating the environment
- `conda env create -f dev_environment.yml`

### Freezing new dependencies
- `conda env export --from-history > dev_environment.yml`

### Updating installed packages while maintaining dev_environment constraints
1. `conda update --all`
2. `pip list --outdated`
3. For each outdated pip package run `pip install --upgrade package-name`
