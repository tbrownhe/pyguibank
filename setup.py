from setuptools import setup, find_packages
import os

# Load the version dynamically (if you use a version.py)
version = {}
version_path = os.path.join("src", "version.py")
if os.path.exists(version_path):
    with open(version_path) as f:
        exec(f.read(), version)

setup(
    name="PyGuiBank",
    version=version.get("__version__", "1.0.0"),  # Default to 0.1.0 if not found
    description="Personal finance manager for parsing, analyzing, and visualizing financial statements.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="tbrownheft@gmail.com",
    url="https://github.com/tbrownheft/pyguibank",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
        "Intended Audience :: End Users/Desktop",
    ],
    keywords="personal finance, GUI, financial analysis, statement parsing",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "PyQt5>=5.15.9",
        "pandas>=2.2.3",
        "matplotlib>=3.9.3",
        "sqlalchemy>=2.0.36",
        "loguru>=0.7.2",
        "scikit-learn>=1.5.2",
        "pdfplumber>=0.11.4",
        "numpy>=2.1.3",
    ],
    # Needs attention:
    extras_require={
        "dev": [
            "pytest>=6.2.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.910",
            "tox>=3.24.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "pyguibank=src.main:main",  # Assumes your main app entry is src/main.py with a `main()` function
        ]
    },
    include_package_data=True,
    package_data={
        "": ["pipeline.mdl"],
    },
    data_files=[
        (
            "model",
            ["pipeline.mdl"],
        ),
    ],
    zip_safe=False,
)
