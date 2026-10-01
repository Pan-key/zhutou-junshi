@echo off
setlocal
cd /d "%~dp0"

REM One-click full build: 猪头军师.exe + 内置 Ollama 运行时 + qwen2.5:7b + Laya 离线快照.
REM Output: dist\猪头军师\猪头军师.exe  —— 整个 dist\猪头军师 文件夹就是发布包，
REM 用户解压后双击 猪头军师.exe 即可，无需装 Ollama、无需下载模型。
REM 只打程序壳（不带模型，先验 UI）：pyinstaller --noconfirm --clean zhutoujunshi.spec

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtualenv .venv ...
    python -m venv .venv || goto :fail
)
call ".venv\Scripts\activate.bat" || goto :fail

echo Installing dependencies ...
python -m pip install -r requirements.txt pyinstaller || goto :fail

echo Assembling runtime + models (Ollama, qwen2.5:7b, Laya) ...
python tools\make_package.py || goto :fail

echo Building ...
pyinstaller --noconfirm --clean zhutoujunshi.spec || goto :fail

echo.
echo Build OK.
echo   %cd%\dist\猪头军师\猪头军师.exe
echo Ship the whole dist\猪头军师 folder: exe needs runtime\ and models\ next to it.
pause
exit /b 0

:fail
echo.
echo Build FAILED. Scroll up for the error.
pause
exit /b 1
