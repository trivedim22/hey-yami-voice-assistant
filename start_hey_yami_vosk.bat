@echo off
REM Hey Yami (Vosk edition) - silent launcher, no console window.
REM Uses the windowless pyw launcher pinned to Python 3.12, where vosk lives.
REM Keep this file in the same folder as hey_yami_vosk.py and the model folder.
cd /d "%~dp0"
start "" pyw -3.12 "%~dp0hey_yami_vosk.py"
