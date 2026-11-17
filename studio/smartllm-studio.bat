@echo off
REM SmartLLM Studio v0.0.1-beta — Windows 11 Launcher (127.0.0.1 only)
setlocal
set "STUDIO_DIR=%~dp0"
for %%I in ("%STUDIO_DIR%..") do set "REPO_ROOT=%%~fI"

set "PYTHON_EXE=%LOCALAPPDATA%\SmartLLM Studio\venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"
)
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

set "PYTHONPATH=%STUDIO_DIR%;%REPO_ROOT%\tools\llama.cpp\gguf-py;%REPO_ROOT%;%PYTHONPATH%"
"%PYTHON_EXE%" -m smartllm_studio.cli %*
endlocal
