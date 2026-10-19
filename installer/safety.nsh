; Refuse an update/uninstall while the desktop app or its backend is still writing.
; Never force-kill a teacher's database in order to replace application files.
!macro customCheckAppRunning
  ${nsProcess::FindProcess} "${APP_EXECUTABLE_FILENAME}" $R0
  ${If} $R0 == 0
    MessageBox MB_OK|MB_ICONEXCLAMATION "Close MoodlIA and wait for Moodle to stop before installing, updating or uninstalling. Your workspace has not been changed." /SD IDOK
    SetErrorLevel 2
    Quit
  ${EndIf}
  ${nsProcess::FindProcess} "moodlia-backend.exe" $R0
  ${If} $R0 == 0
    MessageBox MB_OK|MB_ICONEXCLAMATION "The local Moodle backend is still running. Close MoodlIA and wait for it to stop, then run this installer again. Your workspace has not been changed." /SD IDOK
    SetErrorLevel 2
    Quit
  ${EndIf}
!macroend
