!define APPNAME "InterviewPilot AI"
!define VERSION "1.0.0"
OutFile "release\InterviewPilot-AI-Setup.exe"
InstallDir "$PROGRAMFILES64\InterviewPilot AI"
RequestExecutionLevel admin
Page directory
Page instfiles
Section "Install"
  SetOutPath "$INSTDIR"
  File /r "release\win-unpacked\*.*"
  CreateShortCut "$DESKTOP\InterviewPilot AI.lnk" "$INSTDIR\InterviewPilot AI.exe"
  CreateDirectory "$SMPROGRAMS\InterviewPilot AI"
  CreateShortCut "$SMPROGRAMS\InterviewPilot AI\InterviewPilot AI.lnk" "$INSTDIR\InterviewPilot AI.exe"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd
Section "Uninstall"
  Delete "$DESKTOP\InterviewPilot AI.lnk"
  RMDir /r "$SMPROGRAMS\InterviewPilot AI"
  RMDir /r "$INSTDIR"
SectionEnd
