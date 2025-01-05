; ------------------------------------------------

; Basic info. Admin is required for installing into Program Files.
Name "PyGuiBank"
Outfile "dist\pyguibank_version_setup.exe"
; RequestExecutionLevel admin
Unicode True
InstallDir "$PROGRAMFILES64\PyGuiBank"

; Registry key to check for directory so if you install again, it will overwrite the old one automatically
InstallDirRegKey HKLM "Software\PyGuiBank" "Install_Dir"


; Pages

Page components

; The install directory override page is disabled to prevent user from specifying an important directory.
; Page directory

Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

; ------------------------------------------------

; Installation Options

Section "PyGuiBank" SEC02
    ; This section contains the main program files
    SetOutPath $INSTDIR

    ; Output of PyInstaller
    File /r ".\dist\PyGuiBank\*.*"

    ; Write registry data so windows can track the installation and uninstaller
    WriteRegStr HKLM "SOFTWARE\PyGuiBank" "Install_Dir" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyGuiBank" "DisplayName" "PyGuiBank"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyGuiBank" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyGuiBank" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyGuiBank" "NoRepair" 1
    WriteUninstaller "$INSTDIR\uninstall.exe"

SectionEnd

Section "Start Menu Shortcuts"
  SetOutPath $INSTDIR

  ; Create Start Menu shortcuts
  CreateDirectory "$SMPROGRAMS\PyGuiBank"
  CreateShortcut "$SMPROGRAMS\PyGuiBank\Uninstall.lnk" "$INSTDIR\uninstall.exe"
  CreateShortcut "$SMPROGRAMS\PyGuiBank\PyGuiBank.lnk" "$INSTDIR\PyGuiBank.exe"

SectionEnd

Section "Desktop Shortcut"
  SetOutPath $INSTDIR

  ; Create a desktop shortcut
  CreateShortcut "$DESKTOP\PyGuiBank.lnk" "$INSTDIR\PyGuiBank.exe"

SectionEnd

; ------------------------------------------------

; Uninstaller

Section "Uninstall"

  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyGuiBank"
  DeleteRegKey HKLM "SOFTWARE\PyGuiBank"

  SetOutPath $DESKTOP

  ; Remove shortcuts and start menu folder
  Delete /REBOOTOK "$DESKTOP\PyGuiBank.lnk"
  RMDir /r /REBOOTOK "$SMPROGRAMS\PyGuiBank"

  ; Remove installation files
  ; NOTE THE r FLAG IS NOT SAFE IF YOU ALLOW THE USER TO SPECIFY THEIR OWN INSTALL DIR IN Pages
  RMDir /r /REBOOTOK $INSTDIR

SectionEnd