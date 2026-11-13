@echo off
setlocal
rem Both paths contain spaces. The startup script closes the GUI using exit.
python "%~dp0..\main.py" --vfs "%~dp0..\examples\vfs\several files.xml" --script "%~dp0..\examples\startup with spaces.shell"
exit /b %errorlevel%
