@echo off
set args=
:start
if [%1] == [] goto done
set args=%args% %1
shift
goto start

:done

python tsmc180_main.py %args% 2>&1 | findstr /v /C:"Warning: vin: no DC value"
