@echo off
setlocal
rem Expect exit code 2 for a missing VFS; the GUI must not open.
python "%~dp0..\main.py" --vfs "%~dp0..\examples\missing-vfs" --script "%~dp0..\examples\demo.shell"
if errorlevel 3 exit /b 1
if errorlevel 2 (
    echo Expected configuration error: OK
    exit /b 0
)
exit /b 1
