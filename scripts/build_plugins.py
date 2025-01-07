import compileall
import shutil
from pathlib import Path

src_dir = Path("src/plugins")
dst_dir = Path("dist/plugins")

# Compile all .py files in src/plugins to .pyc files
compileall.compile_dir(src_dir, force=True)

# Get the list of compiled pyfiles.
pyc_fpaths = list(src_dir.glob("**/*/*.pyc"))
pyc_fpaths = [f for f in pyc_fpaths if "__init__" not in f.stem]

for pyc_fpath in pyc_fpaths:
    # Remove the __pycache__ dir and the .cpython-310 in the fname
    rel_path = pyc_fpath.relative_to(src_dir)
    new_rel_path = Path(rel_path.parts[0]) / (
        pyc_fpath.stem.split(".")[0] + pyc_fpath.suffix
    )
    dest_path = dst_dir / new_rel_path

    # Copy the files to the destination
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pyc_fpath, dest_path)

print("Copied .pyc files to dist\plugins")
