#!/bin/bash

# You may need to make this file executable: chmod +x build_macos.sh

set -e

# Navigate to the script directory
cd "$(dirname "$0")" || error_exit "Failed to navigate to script directory."

# Set variables
echo "Setting variables"
VERSION=$(grep "^__version__" ./src/version.py | sed -E "s/__version__ = ['\"]([^'\"]+)['\"]/\1/")
CONDA_ENV="pyguibank"
APP_NAME="PyGuiBank"
DMG_NAME="pyguibank_${VERSION}_macos_setup.dmg"
SRC_DIR="./src"
BUILD_DIR="./build"
DIST_DIR="./dist"
STAGING_DIR="$BUILD_DIR/staging"
APP_PATH="$STAGING_DIR/$APP_NAME.app"
TMP_DMG_PATH="$DIST_DIR/tmp_$DMG_NAME"
DMG_PATH="$DIST_DIR/$DMG_NAME"
VOLUME_PATH="/Volumes/$APP_NAME"
#SERVER_DIR="../pyguibank-server/data/clients/macos"

# Function to handle errors
error_exit() {
    echo "ERROR: $1"
    exit 1
}

# Activate the conda environment
echo "conda activate $CONDA_ENV"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$CONDA_ENV" || error_exit "Failed to activate conda environment."

# Build the executable
echo "Building the executable with PyInstaller..."
pyinstaller \
    -n "$APP_NAME" \
    --clean \
    --noconfirm \
    --noconsole \
    --workpath "prebuild" \
    --distpath "$BUILD_DIR" \
    --paths "$SRC_DIR" \
    --hidden-import=openpyxl.cell._writer \
    --add-data "assets:assets" \
    --icon "assets/pyguibank.png" \
    "$SRC_DIR/main.py" || error_exit "Failed to build the executable."

# PyInstaller splash screen not supported on macos

# Move PyGuiBank.app to its own folder
echo "Moving .app to staging"
mkdir -p $STAGING_DIR
mv "$BUILD_DIR/$APP_NAME.app" "$APP_PATH"
ln -s "/Applications" "$STAGING_DIR/Applications"

# When ready to release for real, $99 annual fee
# Code Signing for APP file
# echo "Code Signing $APP_PATH"
# codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name (Team ID)" "$APP_PATH"
# codesign --verify --verbose dist/PyGuiBank_dmg/PyGuiBank.app

# Ensure the volume is unmounted before mounting
if mount | grep -q "$VOLUME_PATH"; then
    echo "Unmounting existing volume at $VOLUME_PATH"
    hdiutil detach "$VOLUME_PATH"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to unmount "$VOLUME_PATH". Exiting."
        exit 1
    fi
else
    echo "No existing volume at $VOLUME_PATH to unmount."
fi

# Create temp .dmg file and copy staging files there
echo "Loading files into $TMP_DMG_PATH"
mkdir -p "$DIST_DIR"
hdiutil create -size 1000m -fs HFS+ -volname "$APP_NAME" -ov "$TMP_DMG_PATH"
hdiutil attach "$TMP_DMG_PATH"
cp -R "$STAGING_DIR/." "$VOLUME_PATH"

# Pause here to allow the dev to arrange the dmg window
open "$VOLUME_PATH"
open ./assets
echo "Please set the background image of the DMG using Command+J,"
echo "then arrange the icons in the window and CLOSE the window."
echo "When finished, press [ENTER] to continue."
read -p "Press [ENTER] to finalize the DMG..."

# Save the layout, demount the dmg, compress
echo "Finalizing $DMG_PATH"
SetFile -a V "$VOLUME_PATH"
hdiutil detach "$VOLUME_PATH"
hdiutil convert "$TMP_DMG_PATH" -format UDZO -o "$DMG_PATH"

# delete tmp file
echo "Removing $TMP_DMG_PATH"
rm $TMP_DMG_PATH

# Note, this manual stuff can be solved using:
# brew install create-dmg
# create-dmg \
#    --volname "PyGuiBank" \
#    --window-size 500 300 \
#    --background "background.png" \
#    --icon-size 100 \
#    --icon "PyGuiBank.app" 100 100 \
#    --icon "Applications" 300 100 \
#    PyGuiBank.dmg \
#    ~/PyGuiBank_Staging

# Code Signing for DMG file
# codesign --force --sign "Developer ID Application: Your Name (Team ID)" "$DMG_PATH"
# xcrun altool --notarize-app --primary-bundle-id "com.yourcompany.PyGuiBank" --username "your-apple-id" --password "app-specific-password" --file "$DMG_PATH"

# Verify notarization and staple it to the .dmg
# xcrun altool --notarization-info <RequestUUID> --username "your-apple-id" --password "app-specific-password"
# xcrun stapler staple dist/PyGuiBank.dmg

# Copy the dmg to the server directory
#if [ ! -d "$SERVER_DIR" ]; then
#    mkdir -p "$SERVER_DIR" || error_exit "Failed to create server directory."
#fi
#cp "dist/$INSTALLER_NAME" "$SERVER_DIR/" || error_exit "Failed to copy the installer to the server directory."
#echo "Installer successfully copied to $SERVER_DIR."


# Deactivate the conda environment
echo "conda deactivate"
conda deactivate || error_exit "Failed to deactivate conda environment."

echo "Script execution completed successfully!"
