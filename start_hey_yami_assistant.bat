@echo off
REM Hey Yami assistant - silent launcher v2 (absolute pythonw path + fallback).
REM "Wake up Yami" opens Muse; "Hey Yami" starts a talk.
REM The script writes its output to hey_yami_log.txt in this folder.
REM Keep this file in the same folder as hey_yami_assistant.py and the model folder.
cd /d "%~dp0"
set "PYW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if not exist "%PYW%" set "PYW=pyw"
start "" /min "%PYW%" "%~dp0hey_yami_assistant.py"
