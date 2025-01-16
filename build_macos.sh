#!/bin/bash

# You may need to make this file executable: chmod +x build_macos.sh

set -e

# Set variables
#SERVER_DIR="../pyguibank-server/data/clients/macos"
SRCDIR="$(dirname "$0")/src"
CONDA_ENV="pyguibank"

# Function to handle errors
error_exit() {
    echo "ERROR: $1"
    exit 1
}

# Navigate to the script directory
cd "$(dirname "$0")" || error_exit "Failed to navigate to script directory."

# Activate the conda environment
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$CONDA_ENV" || error_exit "Failed to activate conda environment."

# Build the executable
echo "Building the executable with PyInstaller..."
pyinstaller \
    -n "PyGuiBank" \
    --clean \
    --noconfirm \
    --noconsole \
    --workpath "build" \
    --distpath "dist" \
    --paths "$SRCDIR" \
    --hidden-import=openpyxl.cell._writer \
    --add-data "assets:assets" \
    --icon "assets/pyguibank.png" \
    "$SRCDIR/main.py" || error_exit "Failed to build the executable."
    
# Splash screen not supported on macos
#--splash "assets/pyguibank.png" \


# Copy the installer to the server directory
#if [ ! -d "$SERVER_DIR" ]; then
#    mkdir -p "$SERVER_DIR" || error_exit "Failed to create server directory."
#fi
#cp "dist/$INSTALLER_NAME" "$SERVER_DIR/" || error_exit "Failed to copy the installer to the server directory."
#echo "Installer successfully copied to $SERVER_DIR."


# Deactivate the conda environment
echo "Deactivating conda environment..."
conda deactivate || error_exit "Failed to deactivate conda environment."

echo "Script execution completed successfully!"
