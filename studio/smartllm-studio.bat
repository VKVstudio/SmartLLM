@echo off
REM SmartLLM Studio v0.0.7-beta — Windows 11 Launcher (127.0.0.1 only, portable: any folder / any drive)
setlocal EnableExtensions
set "STUDIO_DIR=%~dp0"
for %%I in ("%STUDIO_DIR%..") do set "REPO_ROOT=%%~fI"

set "LOG_DIR=%LOCALAPPDATA%\SmartLLM Studio\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
set "LAUNCHER_LOG=%LOG_DIR%\launcher.log"

set "SILENT_LAUNCH=0"
set "CLI_ARGS="
:parse_args
if "%~1"=="" goto :args_done
if /I "%~1"=="--silent-launch" (
    set "SILENT_LAUNCH=1"
) else (
    if defined CLI_ARGS (
        set "CLI_ARGS=%CLI_ARGS% "%~1""
    ) else (
        set "CLI_ARGS="%~1""
    )
)
shift
goto :parse_args
:args_done

REM --- Python discovery: repo venv -> installed venv -> py 3.12/3.11/3 -> PATH (validated >= 3.11) ---
set "PYTHON_EXE="
for %%C in ("%REPO_ROOT%\.venv\Scripts\python.exe" "%LOCALAPPDATA%\SmartLLM Studio\venv\Scripts\python.exe") do (
    if not defined PYTHON_EXE if exist "%%~C" (
        "%%~C" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
        if not errorlevel 1 set "PYTHON_EXE=%%~C"
    )
)
if not defined PYTHON_EXE (
    for %%V in ("-3.12" "-3.11" "-3") do (
        if not defined PYTHON_EXE (
            for /f "delims=" %%P in ('py %%~V -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1); print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
        )
    )
)
if not defined PYTHON_EXE set "PYTHON_EXE=python"

"%PYTHON_EXE%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: Python 3.11+ required, failed probe: %PYTHON_EXE%>> "%LAUNCHER_LOG%"
    echo SmartLLM Studio: Python 3.11+ is required. Install it with: winget install Python.Python.3.12
    echo Log: "%LAUNCHER_LOG%"
    if not "%SILENT_LAUNCH%"=="1" pause
    exit /b 1
)

set "PYTHONPATH=%STUDIO_DIR%;%REPO_ROOT%\tools\llama.cpp\gguf-py;%REPO_ROOT%"
pushd "%STUDIO_DIR%"
echo [%DATE% %TIME%] launch "%PYTHON_EXE%" -m smartllm_studio.cli %CLI_ARGS%>> "%LAUNCHER_LOG%"
"%PYTHON_EXE%" -m smartllm_studio.cli %CLI_ARGS%
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" (
    echo [%DATE% %TIME%] exit code %RC%>> "%LAUNCHER_LOG%"
    echo SmartLLM Studio exited with code %RC%. Details: "%LAUNCHER_LOG%" and "%APPDATA%\SmartLLM Studio\logs\studio.log"
    if not "%SILENT_LAUNCH%"=="1" pause
)
endlocal & exit /b %RC%
