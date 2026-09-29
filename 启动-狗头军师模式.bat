@echo off
rem JevChat-Windows + 狗头军师 启动脚本
rem 双击本文件即可启动；首次启动会弹设置页，填两把 API key。
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" main.py
