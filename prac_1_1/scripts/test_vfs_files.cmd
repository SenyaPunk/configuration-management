@echo off
setlocal
python "%~dp0..\main.py" --vfs "%~dp0..\examples\vfs\several files.xml" --script "%~dp0..\examples\files.shell"
exit /b %errorlevel%
