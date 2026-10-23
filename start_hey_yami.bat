@echo off
REM Hey Yami listener - silent launcher (no console window)
REM Runs the script from this folder. Train hey_yami.onnx first (README Part A).
cd /d "%~dp0"
start "" /min pythonw "%~dp0hey_yami_oww.py"
