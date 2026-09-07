' ScriptDeck 开机自启 - 静默运行 Flask 服务器

Set WshShell = CreateObject("WScript.Shell")

projectDir = "C:\project\tool\ScriptDeck_Script_Manager"
pythonExe = "C:\ProgramData\anaconda3\envs\python\python.exe"

WshShell.CurrentDirectory = projectDir
WshShell.Run """" & pythonExe & """ main.py", 0, False
