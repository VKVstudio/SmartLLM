' SmartLLM Studio v0.0.1-beta — Windows 11 Silent Background Launcher
Option Explicit
Dim fso, studioDir, batPath, shell
Set fso = CreateObject("Scripting.FileSystemObject")
studioDir = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = fso.BuildPath(studioDir, "smartllm-studio.bat")
Set shell = CreateObject("WScript.Shell")
shell.Run "cmd.exe /c """ & batPath & """", 0, False
