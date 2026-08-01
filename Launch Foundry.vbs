' Launches FoundryDock with no terminal/console window.
' Point your desktop shortcut at THIS file instead of the .bat file.

Set WshShell = CreateObject("WScript.Shell")

appFolder = "C:\Users\nourg\OneDrive\Desktop\Black Feather Foundry\40_Stream Studio\OBS\Scripts\FoundryDock"
WshShell.CurrentDirectory = appFolder

' pythonw.exe runs Python with no console window at all (unlike python.exe).
' The trailing ", 0, False" hides any window and does not wait for it to close.
WshShell.Run "pythonw ""app.py""", 0, False
