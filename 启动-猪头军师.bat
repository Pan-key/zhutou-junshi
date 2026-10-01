@echo off
rem 猪头军师 源码启动脚本：直接跑 .venv 里的 Python，不走打包。
rem 双击即可启动。默认全本地（本地 Laya 判断 + 随包/系统 Ollama 起草），不用填 API key。
rem 跑打包版请用 dist\猪头军师\猪头军师.exe（桌面快捷方式指的就是它）。
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" main.py
