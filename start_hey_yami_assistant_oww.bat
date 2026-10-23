@echo off
REM Hey Yami assistant - openWakeWord (trained TRUE-phrase) edition, silent launcher.
REM "Wake up Yami" opens Muse; "Hey Yami" starts a talk - the real phrases,
REM no soundalikes. Needs hey_yami.onnx + wake_up_yami.onnx next to the script
REM (train them free - see README-training.md).
REM The script writes its output to hey_yami_log.txt in this folder.
cd /d "%~dp0"
set "PYW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if not exist "%PYW%" set "PYW=pyw"
start "" /min "%PYW%" "%~dp0hey_yami_assistant_oww.py"
