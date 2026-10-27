@echo off
setlocal
set VFS_DEMO_FILE=hello.txt
rem Expected command errors are demonstrated; process returns 1 after exit.
python "%~dp0..\main.py" --vfs "%~dp0..\examples\vfs\deep.xml" --script "%~dp0..\examples\all_commands.shell" --continue-on-error
if errorlevel 2 exit /b 1
if errorlevel 1 exit /b 0
exit /b 1
