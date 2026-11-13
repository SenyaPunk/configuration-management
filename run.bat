@echo off
setlocal
if "%~1"=="" set "CONFIG=examples\config.csv"
if not "%~1"=="" set "CONFIG=%~1"
python -m src.dependency_visualizer --config "%CONFIG%" %~2 %~3 %~4 %~5 %~6 %~7 %~8 %~9
exit /b %errorlevel%
