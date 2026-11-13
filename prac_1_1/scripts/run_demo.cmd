@echo off
setlocal
rem Run from any working directory; continue interactively after the script.
python "%~dp0..\main.py" --vfs "%~dp0..\examples\vfs\several files.xml" --script "%~dp0..\examples\demo.shell"
exit /b %errorlevel%
