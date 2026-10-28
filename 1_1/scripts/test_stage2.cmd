@echo off
setlocal
rem Stage 2: CLI configuration, startup scripts, comments and errors.
rem Run the existing stage-specific unit tests without the VFS test suite.
pushd "%~dp0.."
if errorlevel 1 exit /b 1
python -m unittest -v test_shell.ConfigurationTests test_shell.StartupScriptTests
set stage2_result=%errorlevel%
popd
if not "%stage2_result%"=="0" exit /b %stage2_result%

rem Real GUI launch with both CLI parameters and paths containing spaces.
rem The startup script must close the GUI using exit.
call "%~dp0test_paths.cmd"
if errorlevel 1 exit /b 1

rem A missing VFS must produce configuration error code 2 without a GUI.
call "%~dp0test_invalid_config.cmd"
if errorlevel 1 exit /b 1

echo Stage 2: all 13 unit tests and both launch scenarios passed.
exit /b 0
