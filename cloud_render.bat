@echo off
rem usage: cloud_render.bat <episode> [t0 t1]
cd /d "%~dp0"
set PY="C:\Users\Harshveer S. Channa\AppData\Local\Programs\Python\Python314\python.exe"
if "%~2"=="" (%PY% cloud_go.py %1) else (%PY% cloud_go.py %1 --t0 %2 --t1 %3)
pause
