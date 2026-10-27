@echo off
setlocal
python "%~dp0..\main.py" --vfs "%~dp0..\examples\vfs\minimal.xml" --script "%~dp0..\examples\minimal.shell"
exit /b %errorlevel%
