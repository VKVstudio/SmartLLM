@echo off
REM SmartLLM Studio v0.0.3-beta — Windows 11 Launcher (127.0.0.1 only, portable: any folder / any drive)
setlocal EnableExtensions
set "STUDIO_DIR=%~dp0"
for %%I in ("%STUDIO_DIR%..") do set "REPO_ROOT=%%~fI"

set "LOG_DIR=%LOCALAPPDATA%\SmartLLM Studio\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
set "LAUNCHER_LOG=%LOG_DIR%\launcher.log"

REM --- Python discovery: installed venv -> repo venv -> py launcher -> PATH ---
set "PYTHON_EXE="
if exist "%LOCALAPPDATA%\SmartLLM Studio\venv\Scripts\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\SmartLLM Studio\venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist "%REPO_ROOT%\.venv\Scripts\python.exe" set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"
if not defined PYTHON_EXE (
    for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
)
if not defined PYTHON_EXE set "PYTHON_EXE=python"

"%PYTHON_EXE%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: Python 3.11+ required, failed probe: %PYTHON_EXE%>> "%LAUNCHER_LOG%"
    echo SmartLLM Studio: Python 3.11+ is required. Install it with: winget install Python.Python.3.12
    echo Log: "%LAUNCHER_LOG%"
    if not "%~1"=="--silent-launch" pause
    exit /b 1
)

set "PYTHONPATH=%STUDIO_DIR%;%REPO_ROOT%\tools\llama.cpp\gguf-py;%REPO_ROOT%"
pushd "%STUDIO_DIR%"
echo [%DATE% %TIME%] launch "%PYTHON_EXE%" -m smartllm_studio.cli %*>> "%LAUNCHER_LOG%"
"%PYTHON_EXE%" -m smartllm_studio.cli %*
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" (
    echo [%DATE% %TIME%] exit code %RC%>> "%LAUNCHER_LOG%"
    echo SmartLLM Studio exited with code %RC%. Details: "%LAUNCHER_LOG%" and "%LOG_DIR%\studio.log"
    if not "%~1"=="--silent-launch" pause
)
endlocal & exit /b %RC%