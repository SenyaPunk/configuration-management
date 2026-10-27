@echo off
setlocal
rem Expect a line 5 error in the GUI. Close the window or enter exit; code 1.
python "%~dp0..\main.py" --vfs "%~dp0..\examples\vfs\several files.xml" --script "%~dp0..\examples\error.shell"
exit /b %errorlevel%
