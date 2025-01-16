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


## MacOS

### Bypassing Gatekeeper
Applications `.app` and `.dmg` will be blocked by Apple Gatekeeper unless signed and notarized. This can be bypassed by end users by following these steps:
1. Open the App.
2. Got to System Preferences > Security & Privacy.
3. In the General tab, under the message about the blocked app, click the button that says "Open Anyway".
4. Click Open to confirm.


### 1. Register as an Apple Developer
To access the tools for code signing and notarization, you need an Apple Developer account:

a. Create an Apple ID
If you don’t already have an Apple ID, create one. Visit Apple ID website and follow the steps to create an account.

b. Enroll in the Apple Developer Program
Go to the Apple Developer Program enrollment page.
Click Enroll and sign in with your Apple ID.
Follow the steps to provide your details (name, address, etc.).
Pay the annual fee of $99 (USD).

### 2. Set Up Code Signing Certificates
After enrolling, you need to create and install code signing certificates:

a. Open Keychain Access
Open Keychain Access on your Mac (search for it in Spotlight).
From the Keychain Access menu, select Certificate Assistant > Request a Certificate from a Certificate Authority.

b. Request a Signing Certificate
Enter your Apple Developer account email in the Certificate Assistant.
Choose Saved to disk as the request method and save the .certSigningRequest file.
Go to the Apple Developer Certificates page.
Click the + icon and choose Developer ID Application.
Upload the .certSigningRequest file you saved earlier.
Download and install the certificate into your Keychain.

### 3. Configure Your macOS Environment
Once the certificate is installed, you can sign your app and .dmg file.

a. Verify the Certificate
Ensure your certificate is available by running:
`security find-identity -v -p codesigning`
You should see your Developer ID Application certificate in the output.

b. Sign Your Application
Use the codesign tool to sign your .app file:
`codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name (Team ID)" dist/PyGuiBank.app`

c. Verify the Signing
To verify that your app is correctly signed:
`codesign --verify --verbose dist/PyGuiBank.app`
`spctl --assess --verbose dist/PyGuiBank.app`

### 4. Notarize Your Application
Notarization ensures your app passes macOS Gatekeeper checks.

a. Submit Your App
Use the altool command to submit your app for notarization:
`xcrun altool --notarize-app --primary-bundle-id "com.yourcompany.PyGuiBank" --username "your-apple-id" --password "app-specific-password" --file dist/PyGuiBank.dmg`
- Replace "your-apple-id" with your Apple ID email.
- Replace "app-specific-password" with an App-Specific Password.
- Replace "com.yourcompany.PyGuiBank" with your app's bundle identifier.

b. Check Notarization Status
After submitting, check the notarization status:
`xcrun altool --notarization-info <RequestUUID> --username "your-apple-id" --password "app-specific-password"`

c. Staple the Notarization
Once notarization is successful, staple the notarization ticket to your .dmg:
`xcrun stapler staple dist/PyGuiBank.dmg`

